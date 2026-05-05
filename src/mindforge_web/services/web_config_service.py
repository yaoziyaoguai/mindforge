"""Secret-safe Web configuration status.

中文学习型说明：Web 需要告诉用户“哪些 key 已配置”，但绝不能泄露 key 的值。
因此本模块只做 `.env` 文件的 key presence 解析，并且不把 value 写入
`os.environ`。provider readiness 仍复用 `mindforge.provider_readiness`。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mindforge.config import MindForgeConfig
from mindforge.cubox_readiness import classify_cubox_real_opt_in, inspect_cubox_config
from mindforge.provider_readiness import build_readiness_report

from mindforge_web.schemas import (
    EnvKeyStatus,
    NextAction,
    ProviderAliasStatus,
    ProviderStatus,
    StatusItem,
)


@dataclass(frozen=True)
class DotenvPresence:
    path: Path | None
    keys: frozenset[str]


class WebConfigService:
    """配置状态读取边界；只返回 secret-safe metadata。"""

    def __init__(self, cfg: MindForgeConfig, *, cwd: Path | None = None) -> None:
        self.cfg = cfg
        self.cwd = cwd or Path.cwd()

    def env_key_statuses(self) -> list[EnvKeyStatus]:
        dotenv = self._read_dotenv_presence()
        names = sorted(self._interesting_env_names())
        statuses: list[EnvKeyStatus] = []
        for name in names:
            sources: list[str] = []
            if name in os.environ:
                sources.append("process")
            if name in dotenv.keys:
                sources.append(".env")
            statuses.append(
                EnvKeyStatus(name=name, configured=bool(sources), sources=sources)
            )
        return statuses

    def provider_status(self) -> ProviderStatus:
        report = build_readiness_report(self.cfg.llm)
        provider = report["provider"]
        opt_in = report["opt_in"]
        return ProviderStatus(
            active_profile=provider["active_profile"],
            opt_in_state=opt_in["opt_in_state"],
            can_run_real_smoke=opt_in["can_run_real_smoke"],
            aliases=[
                ProviderAliasStatus(
                    alias=a["alias"],
                    type=a["type"],
                    in_active_profile=a["in_active_profile"],
                    api_key_env=a.get("api_key_env"),
                    api_key_present=bool(a.get("api_key_present")),
                    base_url_env_present=bool(a.get("base_url_env_present")),
                )
                for a in provider["aliases"]
            ],
            blockers=list(opt_in["blockers"]),
        )

    def cubox_status_item(self) -> StatusItem:
        report = inspect_cubox_config()
        classification = classify_cubox_real_opt_in(report, allow_real=False)
        token_present = bool(report.get("token_present", False))
        return StatusItem(
            key="cubox",
            label="Cubox JSON export",
            status="ok" if token_present else "info",
            value="token configured" if token_present else "JSON export path available",
            detail=str(classification.get("next_action", "")),
            next_action=NextAction(
                label="Use JSON export",
                description="真实 Cubox HTTP ingestion 尚未开放；先使用本地 JSON export。",
                command="mindforge cubox dry-run --export <file.json>",
            ),
        )

    def _interesting_env_names(self) -> set[str]:
        names: set[str] = {"MINDFORGE_CUBOX_TOKEN"}
        for model in self.cfg.llm.models.values():
            for value in (
                model.api_key_env,
                model.base_url_env,
                model.version_env,
                model.model_env,
            ):
                if value:
                    names.add(value)
        return names

    def _read_dotenv_presence(self) -> DotenvPresence:
        path = self._find_dotenv(self.cwd)
        if path is None:
            return DotenvPresence(path=None, keys=frozenset())
        keys: set[str] = set()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return DotenvPresence(path=path, keys=frozenset())
        for line in text.splitlines():
            parsed = self._parse_env_key(line)
            if parsed:
                keys.add(parsed)
        return DotenvPresence(path=path, keys=frozenset(keys))

    @staticmethod
    def _find_dotenv(start: Path) -> Path | None:
        cur = start.resolve()
        for path in (cur, *cur.parents):
            candidate = path / ".env"
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _parse_env_key(line: str) -> str | None:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            return None
        key, _sep, _value = stripped.partition("=")
        key = key.removeprefix("export ").strip()
        return key if key.isidentifier() else None
