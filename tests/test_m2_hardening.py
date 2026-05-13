"""M2.5 加固测试 — 失败路径 + runs jsonl 字段白名单 + 不泄漏。

覆盖：
- model_alias 不存在（factory build 失败 / LLMClient 解析失败）
- stage 在 active_profile 中缺失
- LLM 返回非 JSON / 非法结构 → 该 item status=failed，runs jsonl 留痕但不泄漏
- runs/*.jsonl 只包含字段白名单；禁止出现 api_key / Authorization / raw_text /
  prompt 全文 / completion 全文 / request body / response body
- 原始 source 文件全程不被改写
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.llm import LLMClient, build_providers
from mindforge.llm.base import LLMRequest, LLMResult, LLMProvider
from mindforge.run_logger import _ALLOWED_FIELDS

runner = CliRunner()

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
TEMPLATE_PATH = REPO_ROOT / "templates" / "knowledge_card.md.j2"
TRACKS_PATH = REPO_ROOT / "configs" / "learning_tracks.yaml"

# llm_call 事件允许出现的字段（白名单严格子集）
_LLM_CALL_ALLOWED = {
    "event",
    "ts",
    "run_id",
    "stage",
    "model_alias",
    "provider",
    "provider_type",
    "actual_model",
    "prompt_version",
    "input_file_hash",
    "status",
    "error_message",
    "tokens_in",
    "tokens_out",
    "latency_ms",
}


# ---------------------------------------------------------------------------
# config / client level: 不存在的 alias / stage 必须安全失败
# ---------------------------------------------------------------------------


def test_build_providers_unknown_type_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from mindforge.config import load_mindforge_config

    cfg_text = """
version: 0.1
vault: {root: "/tmp/v", inbox_root: "00-Inbox", cards_dir: "20-Knowledge-Cards", archive_dir: "90-Archive/Skipped"}
sources:
  enabled: [plain_markdown]
  registry:
    plain_markdown: {adapter: PlainMarkdownAdapter, inbox_subdir: "ManualNotes", file_glob: "*.md", enabled: true}
state: {workdir: "/tmp/.mf", state_file: "state.json", runs_dir: "runs", index_file: "index.jsonl"}
triage: {value_score_threshold: 5, default_track: "unrouted"}
llm:
  active_profile: bad
  profiles:
    bad: {triage: m1, distill: m1, link_suggestion: m1, review_questions: m1, action_extraction: m1}
  models:
    m1:
      provider: x
      type: never_heard_of_this
      base_url: "x://"
      model: x
prompts:
  triage_version: v1
  distill_version: v1
  link_suggestion_version: v1
  review_questions_version: v1
  action_extraction_version: v1
logging: {level: INFO, file: "/tmp/x.log"}
"""
    p = Path("/tmp/_mf_bad.yaml")
    p.write_text(cfg_text, "utf-8")
    cfg = load_mindforge_config(p)
    from mindforge.llm import ProviderError
    with pytest.raises(ProviderError, match="never_heard_of_this"):
        build_providers(cfg.llm)


def test_llm_client_unknown_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    """profile 中没有声明的 stage → resolve 失败但不泄漏配置 secret。"""

    class _Cfg:
        active_profile = "p"
        profiles = {"p": {"triage": "m1"}}  # 故意缺其他 stage
        models = {
            "m1": type(
                "MC",
                (),
                {
                    "alias": "m1",
                    "provider": "fake",
                    "type": "fake",
                    "base_url": "fake://",
                    "model": "x",
                    "timeout_seconds": 10,
                    "max_retries": 0,
                    "api_key_env": None,
                    "api_key_optional": True,
                    "base_url_env": None,
                    "version_env": None,
                    "model_env": None,
                },
            )(),
        }

        def resolve_stage(self, s):
            return self.models[self.profiles[self.active_profile][s]]

    from mindforge.llm.fake import FakeProvider
    client = LLMClient(llm_config=_Cfg(), providers={"m1": FakeProvider()})
    with pytest.raises(KeyError):
        client.resolve_model_for_stage("distill")


# ---------------------------------------------------------------------------
# 端到端：LLM 返回非 JSON → process 标 failed，runs jsonl 留痕、白名单
# ---------------------------------------------------------------------------


class _BadJsonProvider(LLMProvider):
    """每次都返回非 JSON 的 provider；用来触发 stage 解析失败。"""

    type = "fake"
    name = "bad_json"

    def generate(self, request: LLMRequest) -> LLMResult:
        # 故意返回散文，且包含一段"看似敏感"的 token，以验证脱敏：实际我们
        # 只关心 runs jsonl 不会回显 LLM 输出全文 → 该 token 不应出现。
        return LLMResult(
            text="抱歉这次没有按 JSON 输出 SECRET-COMPLETION-TOKEN 你看不到吧",
            tokens_in=10,
            tokens_out=20,
            latency_ms=5,
            raw=None,
        )


def _build_vault_with_provider(tmp_path: Path) -> tuple[Path, Path, Path]:
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)
    src = vault / "00-Inbox" / "ManualNotes" / "n1.md"
    src.write_text(
        "---\ntitle: SECRET-PROMPT-TOKEN\n---\n\n本文包含 SECRET-PROMPT-TOKEN，看下游会不会泄漏。\n",
        encoding="utf-8",
    )
    cfg = {
        "version": 0.1,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {
            "enabled": ["plain_markdown"],
            "registry": {
                "plain_markdown": {
                    "adapter": "PlainMarkdownAdapter",
                    "inbox_subdir": "ManualNotes",
                    "file_glob": "*.md",
                    "enabled": True,
                }
            },
        },
        "state": {
            "workdir": str(tmp_path / ".mindforge"),
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "f",
                    "distill": "f",
                    "link_suggestion": "f",
                    "review_questions": "f",
                    "action_extraction": "f",
                }
            },
            "models": {
                "f": {
                    "provider": "bad_json_local",
                    "type": "fake",
                    "model": "fake-bad",
                }
            },
        },
        "prompts": {
            "triage_version": "v1",
            "distill_version": "v1",
            "link_suggestion_version": "v1",
            "review_questions_version": "v1",
            "action_extraction_version": "v1",
        },
        "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
    }
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return cfg_path, vault, src


def test_invalid_llm_json_marks_failed_without_leakage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, vault, src = _build_vault_with_provider(tmp_path)
    src_before = src.read_text("utf-8")

    # 让 factory 把 type=fake 路由到我们的 BadJson provider
    # 需同时 patch mindforge.llm（re-export 路径）和 mindforge.llm.factory（源定义）
    bad = {"f": _BadJsonProvider()}
    monkeypatch.setattr(
        "mindforge.llm.build_providers",
        lambda *a, **kw: bad,
    )
    monkeypatch.setattr(
        "mindforge.llm.factory.build_providers",
        lambda *a, **kw: bad,
    )

    r = runner.invoke(
        app,
        [
            "process",
            "--config", str(cfg_path),
            "--prompts-dir", str(PROMPTS_DIR),
            "--tracks", str(TRACKS_PATH),
            "--template", str(TEMPLATE_PATH),
        ],
    )
    assert r.exit_code == 0, r.output
    assert "failed=1" in r.output

    # 卡片不被写出
    assert list((vault / "20-Knowledge-Cards").rglob("*.md")) == []

    # 原始 source 内容 100% 不变
    assert src.read_text("utf-8") == src_before

    # runs jsonl 必含一条 status=failed 的 llm_call，但不能含 prompt/completion 全文
    runs = list((tmp_path / ".mindforge" / "runs").glob("*.jsonl"))
    assert len(runs) == 1
    events = [json.loads(line) for line in runs[0].read_text("utf-8").splitlines() if line.strip()]
    flat = json.dumps(events, ensure_ascii=False)

    # 1) 不能泄漏的字段值
    for forbidden in (
        "SECRET-PROMPT-TOKEN",          # source 正文/title
        "SECRET-COMPLETION-TOKEN",      # provider 完成文本
        "raw_text",                     # 字段名本身也不应作 key 出现
        "Authorization",
        "x-api-key",
        "api_key",
    ):
        assert forbidden not in flat, f"runs jsonl leaked {forbidden!r}"

    # 2) llm_call 字段必须是白名单子集
    llm_calls = [e for e in events if e["event"] == "llm_call"]
    assert llm_calls, "expected at least one llm_call event"
    for c in llm_calls:
        extra = set(c) - _LLM_CALL_ALLOWED
        assert not extra, f"llm_call has unwhitelisted fields: {extra}"
    # 3) 至少一条 failed
    assert any(c["status"] == "failed" for c in llm_calls)

    # 4) 全局：所有事件字段必须在 run_logger 主白名单里（含 event/ts/run_id 这些）
    for e in events:
        for k in e:
            if k in ("event", "ts", "run_id"):
                continue
            assert k in _ALLOWED_FIELDS, f"event {e['event']} has unwhitelisted field {k!r}"
