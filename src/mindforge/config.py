"""配置加载与校验 — 加载 ``configs/mindforge.yaml`` 与 ``learning_tracks.yaml``。

设计原则
========

1. **fail-fast**
   - 配置错误（active_profile 找不到、source_type 不在 enum、stage 缺失）
     必须在启动时立即报错，不允许进入处理循环后再炸。

2. **配置层面开放、执行层面克制**
   - 允许用户列任意多个 profile / model；
   - 但 ``active_profile`` 一次只激活一组静态映射；
   - 不做 fallback / 投票 / 动态路由。

3. **本模块只负责 LOAD + VALIDATE**
   - 不持有 LLMClient、不读 inbox、不写 state；
   - 它的输出（``MindForgeConfig``）就是其他模块唯一可信的配置视图。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# v0.1 固定的 5 个 stage（与 prompts/ 下子目录一一对应）
REQUIRED_STAGES: tuple[str, ...] = (
    "triage",
    "distill",
    "link_suggestion",
    "review_questions",
    "action_extraction",
)

# v0.1 已知的 source_type，必须与 mindforge.sources.base.SourceType 同步
KNOWN_SOURCE_TYPES: frozenset[str] = frozenset(
    {
        "cubox_markdown",
        "plain_markdown",
        "webclip_markdown",
        "pdf",
        "docx",
        "chat_export",
        "manual_note",
        "obsidian_note",
    }
)


class ConfigError(ValueError):
    """配置加载或校验失败。统一异常，方便 CLI 友好提示。"""


# ---------------------------------------------------------------------------
# Dataclass 视图（其他模块只读这些结构，不直接读 yaml dict）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VaultConfig:
    root: Path
    inbox_root: str
    cards_dir: str
    archive_dir: str
    projects_dir: str = "30-Projects"

    @property
    def inbox_path(self) -> Path:
        return self.root / self.inbox_root

    @property
    def cards_path(self) -> Path:
        return self.root / self.cards_dir

    @property
    def projects_path(self) -> Path:
        return self.root / self.projects_dir


@dataclass(frozen=True)
class SourceRegistryEntry:
    source_type: str
    adapter: str
    inbox_subdir: str
    file_glob: str
    enabled: bool

    @property
    def is_enabled(self) -> bool:
        return self.enabled


@dataclass(frozen=True)
class SourcesConfig:
    enabled: tuple[str, ...]                          # 白名单
    registry: dict[str, SourceRegistryEntry]          # source_type -> entry

    def active_entries(self) -> list[SourceRegistryEntry]:
        """返回真正激活的 adapter 配置（白名单 ∩ enabled=true）。"""
        return [
            self.registry[st]
            for st in self.enabled
            if st in self.registry and self.registry[st].is_enabled
        ]


@dataclass(frozen=True)
class StateConfig:
    workdir: Path
    state_file: str
    runs_dir: str
    index_file: str
    backup_state: bool

    @property
    def state_path(self) -> Path:
        return self.workdir / self.state_file

    @property
    def runs_path(self) -> Path:
        return self.workdir / self.runs_dir


@dataclass(frozen=True)
class TriageConfig:
    value_score_threshold: int
    default_track: str


@dataclass(frozen=True)
class ReviewIntervals:
    """review mark 写卡片时按 result 计算 next review_after 的间隔（天）。

    见 docs/M4_RECALL_REVIEW_PROTOCOL.md §0 #1 / §4。"""

    remembered: int = 14
    partial: int = 7
    forgotten: int = 1


@dataclass(frozen=True)
class ReviewConfig:
    """M4 review 子系统配置（可选；缺失时全部走默认）。"""

    intervals: ReviewIntervals = field(default_factory=ReviewIntervals)
    default_include_drafts: bool = False


@dataclass(frozen=True)
class ModelConfig:
    alias: str
    provider: str
    type: str
    base_url: str
    model: str
    timeout_seconds: int
    max_retries: int
    api_key_env: str | None = None
    api_key_optional: bool = False
    base_url_env: str | None = None     # 优先级高于 base_url；运行时由 provider 解析
    version_env: str | None = None      # 仅 anthropic_compatible 使用（anthropic-version 头）
    model_env: str | None = None        # 模型名也允许从 env 覆盖（场景：同 endpoint 切换不同模型）


@dataclass(frozen=True)
class LLMConfig:
    active_profile: str
    profiles: dict[str, dict[str, str]]               # profile_name -> {stage: alias}
    models: dict[str, ModelConfig]                    # alias -> ModelConfig

    def resolve_stage(self, stage: str) -> ModelConfig:
        """按当前 active_profile 把 stage 解析为 ModelConfig。"""
        profile = self.profiles[self.active_profile]
        alias = profile[stage]
        return self.models[alias]


@dataclass(frozen=True)
class PromptVersions:
    triage: str
    distill: str
    link_suggestion: str
    review_questions: str
    action_extraction: str

    def for_stage(self, stage: str) -> str:
        return getattr(self, stage)


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    file: str
    record_prompts: bool
    record_outputs: bool


@dataclass(frozen=True)
class TelemetryConfig:
    """M5.7 — 本地 telemetry 子配置（详见 docs/M5_7_TELEMETRY_PROTOCOL.md）。

    - ``enabled``：False 时模块完全静默，不写盘；
    - ``local_only``：v0.2.3 固定 True；任何远程 sink 都需要先扩协议。
    """

    enabled: bool = True
    local_only: bool = True


@dataclass(frozen=True)
class ObsidianConfig:
    """v0.5 — Obsidian binding 配置。

    Obsidian vault 是个人知识语境 source，不是 MindForge runtime state 目录。
    因此默认只读，且 staging/review 与 runtime 目录在配置层面分开。
    """

    vault_path: Path | None = None
    staging_dir: str = "90-System/MindForge/Staging"
    review_dir: str = "90-System/MindForge/Review"
    include_dirs: tuple[str, ...] = ("00-Inbox", "02-Knowledge", "03-Projects")
    exclude_dirs: tuple[str, ...] = (
        ".obsidian",
        ".git",
        ".mindforge",
        "90-System/MindForge/Runtime",
    )
    read_only: bool = True


@dataclass(frozen=True)
class BM25SearchConfig:
    """v0.3.1 — BM25 字段权重 + 超参的可配置子结构。

    设计：**配置层面开放、执行层面克制**。
    - 字段权重缺失或为 0 → 该字段不索引；
    - 非数值 / 负数 → ConfigError，给出可操作信息；
    - 完全缺失 → 走 ``DEFAULT_FIELD_WEIGHTS``，新用户零配置即可用。

    字段名采用"用户友好别名"，与 `lexical_index.DEFAULT_FIELD_WEIGHTS`
    的内部 field 名一一映射；映射表见 `_FIELD_ALIAS_TO_INTERNAL`。
    """

    enabled: bool = True
    k1: float = 1.5
    b: float = 0.75
    default_limit: int = 10
    fields: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class HybridSearchConfig:
    """v0.3.1 — hybrid ranking 权重配置。

    hybrid 仍然是**纯本地规则排序**，不是 RAG / embedding：
    final = w_bm25 * bm25_norm + w_value * value_norm + w_review * review_due
    各分量缺失时按 0 处理（不失败）。
    """

    enabled: bool = True
    weights: dict[str, float] = field(default_factory=lambda: {
        "bm25": 0.75, "value_score": 0.15, "review_due": 0.10,
    })


@dataclass(frozen=True)
class SearchConfig:
    """v0.3.1 — search 顶层配置（覆盖 BM25 与 hybrid 两块）。"""

    bm25: BM25SearchConfig = field(default_factory=BM25SearchConfig)
    hybrid: HybridSearchConfig = field(default_factory=HybridSearchConfig)


@dataclass(frozen=True)
class MindForgeConfig:
    """整份配置的不可变快照。其他模块只依赖这个对象。"""

    version: float
    vault: VaultConfig
    sources: SourcesConfig
    state: StateConfig
    triage: TriageConfig
    llm: LLMConfig
    prompts: PromptVersions
    logging: LoggingConfig
    review: ReviewConfig = field(default_factory=ReviewConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    obsidian: ObsidianConfig = field(default_factory=ObsidianConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    raw: dict[str, Any] = field(default_factory=dict)  # 便于调试


@dataclass(frozen=True)
class TrackConfig:
    id: str
    keywords: tuple[str, ...]
    negative_keywords: tuple[str, ...]
    output_focus: tuple[str, ...]


@dataclass(frozen=True)
class LearningTracksConfig:
    version: int
    tracks: tuple[TrackConfig, ...]

    def by_id(self, track_id: str) -> TrackConfig | None:
        for t in self.tracks:
            if t.id == track_id:
                return t
        return None


# ---------------------------------------------------------------------------
# Loader + Validator
# ---------------------------------------------------------------------------


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"配置文件不存在：{path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML 解析失败 {path}: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"{path} 顶层必须是 YAML 对象，得到 {type(data).__name__}")
    return data


def load_mindforge_config(path: str | Path) -> MindForgeConfig:
    """加载并校验 mindforge.yaml，返回不可变快照。"""
    p = Path(path)
    raw = _read_yaml(p)
    base_dir = p.parent.parent  # configs/mindforge.yaml -> 项目根

    # ---- vault ----
    vault_raw = _require(raw, "vault", dict, ctx=str(p))
    vault = VaultConfig(
        root=Path(_require(vault_raw, "root", str, ctx="vault")).expanduser(),
        inbox_root=_require(vault_raw, "inbox_root", str, ctx="vault"),
        cards_dir=_require(vault_raw, "cards_dir", str, ctx="vault"),
        archive_dir=_require(vault_raw, "archive_dir", str, ctx="vault"),
        projects_dir=str(vault_raw.get("projects_dir") or "30-Projects"),
    )

    # ---- sources ----
    sources_raw = _require(raw, "sources", dict, ctx=str(p))
    enabled_list = _require(sources_raw, "enabled", list, ctx="sources")
    registry_raw = _require(sources_raw, "registry", dict, ctx="sources")

    registry: dict[str, SourceRegistryEntry] = {}
    for st, entry in registry_raw.items():
        if st not in KNOWN_SOURCE_TYPES:
            raise ConfigError(
                f"sources.registry 出现未知 source_type {st!r}；"
                f"已知集合：{sorted(KNOWN_SOURCE_TYPES)}"
            )
        if not isinstance(entry, dict):
            raise ConfigError(f"sources.registry.{st} 必须是 YAML 对象")
        registry[st] = SourceRegistryEntry(
            source_type=st,
            adapter=_require(entry, "adapter", str, ctx=f"sources.registry.{st}"),
            inbox_subdir=_require(entry, "inbox_subdir", str, ctx=f"sources.registry.{st}"),
            file_glob=_require(entry, "file_glob", str, ctx=f"sources.registry.{st}"),
            # enabled 字段在 v0.1 默认 True；显式 false 表示占位 stub
            enabled=bool(entry.get("enabled", True)),
        )
    for st in enabled_list:
        if st not in registry:
            raise ConfigError(
                f"sources.enabled 列出的 {st!r} 不在 sources.registry 中"
            )
    sources = SourcesConfig(enabled=tuple(enabled_list), registry=registry)

    # ---- state ----
    state_raw = _require(raw, "state", dict, ctx=str(p))
    workdir_str = _require(state_raw, "workdir", str, ctx="state")
    state = StateConfig(
        workdir=(base_dir / workdir_str) if not Path(workdir_str).is_absolute() else Path(workdir_str),
        state_file=_require(state_raw, "state_file", str, ctx="state"),
        runs_dir=_require(state_raw, "runs_dir", str, ctx="state"),
        index_file=_require(state_raw, "index_file", str, ctx="state"),
        backup_state=bool(state_raw.get("backup_state", True)),
    )

    # ---- triage ----
    triage_raw = _require(raw, "triage", dict, ctx=str(p))
    triage = TriageConfig(
        value_score_threshold=int(_require(triage_raw, "value_score_threshold", int, ctx="triage")),
        default_track=_require(triage_raw, "default_track", str, ctx="triage"),
    )

    # ---- llm ----
    llm = _parse_llm(_require(raw, "llm", dict, ctx=str(p)))

    # ---- prompts ----
    prompts_raw = _require(raw, "prompts", dict, ctx=str(p))
    prompts = PromptVersions(
        triage=_require(prompts_raw, "triage_version", str, ctx="prompts"),
        distill=_require(prompts_raw, "distill_version", str, ctx="prompts"),
        link_suggestion=_require(prompts_raw, "link_suggestion_version", str, ctx="prompts"),
        review_questions=_require(prompts_raw, "review_questions_version", str, ctx="prompts"),
        action_extraction=_require(prompts_raw, "action_extraction_version", str, ctx="prompts"),
    )

    # ---- logging ----
    logging_raw = _require(raw, "logging", dict, ctx=str(p))
    logging_cfg = LoggingConfig(
        level=str(logging_raw.get("level", "INFO")),
        file=str(logging_raw.get("file", ".mindforge/mindforge.log")),
        record_prompts=bool(logging_raw.get("record_prompts", True)),
        record_outputs=bool(logging_raw.get("record_outputs", True)),
    )

    # ---- review (M4 — optional block；缺失走全默认) ----
    review_raw = raw.get("review") or {}
    if not isinstance(review_raw, dict):
        raise ConfigError(f"review 必须是 YAML 对象，得到 {type(review_raw).__name__}")
    intervals_raw = review_raw.get("intervals") or {}
    if not isinstance(intervals_raw, dict):
        raise ConfigError("review.intervals 必须是 YAML 对象")
    intervals = ReviewIntervals(
        remembered=int(intervals_raw.get("remembered", 14)),
        partial=int(intervals_raw.get("partial", 7)),
        forgotten=int(intervals_raw.get("forgotten", 1)),
    )
    for fname, val in (
        ("remembered", intervals.remembered),
        ("partial", intervals.partial),
        ("forgotten", intervals.forgotten),
    ):
        if val < 0:
            raise ConfigError(f"review.intervals.{fname} 必须 >=0，得到 {val}")
    review_cfg = ReviewConfig(
        intervals=intervals,
        default_include_drafts=bool(review_raw.get("default_include_drafts", False)),
    )

    # ---- telemetry (M5.7 — optional block；缺失走全默认) ----
    telemetry_raw = raw.get("telemetry") or {}
    if not isinstance(telemetry_raw, dict):
        raise ConfigError(
            f"telemetry 必须是 mapping，得到 {type(telemetry_raw).__name__}"
        )
    telemetry_cfg = TelemetryConfig(
        enabled=bool(telemetry_raw.get("enabled", True)),
        local_only=bool(telemetry_raw.get("local_only", True)),
    )

    # ---- obsidian (v0.5 — optional；缺失走安全默认) ----
    obsidian_cfg = _parse_obsidian(raw.get("obsidian") or {})

    # ---- search (v0.3.1 — optional；缺失走全默认) ----
    search_cfg = _parse_search(raw.get("search") or {})

    return MindForgeConfig(
        version=float(raw.get("version", 0.1)),
        vault=vault,
        sources=sources,
        state=state,
        triage=triage,
        llm=llm,
        prompts=prompts,
        logging=logging_cfg,
        review=review_cfg,
        telemetry=telemetry_cfg,
        obsidian=obsidian_cfg,
        search=search_cfg,
        raw=raw,
    )


def _parse_obsidian(raw: Any) -> "ObsidianConfig":
    if not isinstance(raw, dict):
        raise ConfigError(f"obsidian 必须是 YAML 对象，得到 {type(raw).__name__}")
    vault_text = str(raw.get("vault_path") or "").strip()
    include_dirs = raw.get("include_dirs") or ["00-Inbox", "02-Knowledge", "03-Projects"]
    exclude_dirs = raw.get("exclude_dirs") or [
        ".obsidian",
        ".git",
        ".mindforge",
        "90-System/MindForge/Runtime",
    ]
    if not isinstance(include_dirs, list):
        raise ConfigError("obsidian.include_dirs 必须是列表")
    if not isinstance(exclude_dirs, list):
        raise ConfigError("obsidian.exclude_dirs 必须是列表")
    staging_dir = str(raw.get("staging_dir") or "90-System/MindForge/Staging").strip()
    review_dir = str(raw.get("review_dir") or "90-System/MindForge/Review").strip()
    if not staging_dir or not review_dir:
        raise ConfigError("obsidian.staging_dir / review_dir 不能为空")
    return ObsidianConfig(
        vault_path=Path(vault_text).expanduser() if vault_text else None,
        staging_dir=staging_dir,
        review_dir=review_dir,
        include_dirs=tuple(str(x).strip().strip("/") for x in include_dirs if str(x).strip()),
        exclude_dirs=tuple(str(x).strip().strip("/") for x in exclude_dirs if str(x).strip()),
        read_only=bool(raw.get("read_only", True)),
    )


def _parse_search(raw: Any) -> "SearchConfig":
    """解析可选 search 块；缺失或空走默认。

    设计契约（v0.3.1）：
    - 字段权重必须 >=0；负数 / 非数值 → ConfigError；
    - k1 / b 必须 >0；
    - hybrid weights 必须 >=0；全 0 等价于关闭 hybrid（仍允许，调用方给提示）。
    """
    if not isinstance(raw, dict):
        raise ConfigError(f"search 必须是 YAML 对象，得到 {type(raw).__name__}")

    bm25_raw = raw.get("bm25") or {}
    if not isinstance(bm25_raw, dict):
        raise ConfigError("search.bm25 必须是 YAML 对象")
    fields_raw = bm25_raw.get("fields") or {}
    if not isinstance(fields_raw, dict):
        raise ConfigError("search.bm25.fields 必须是 YAML 对象：{field_name: weight}")
    fields_clean: dict[str, float] = {}
    for k, v in fields_raw.items():
        try:
            fv = float(v)
        except (TypeError, ValueError) as e:
            raise ConfigError(
                f"search.bm25.fields.{k}={v!r} 必须是数值（建议 0.0~10.0）"
            ) from e
        if fv < 0:
            raise ConfigError(
                f"search.bm25.fields.{k}={fv} 必须 >=0；权重 0 表示该字段不索引"
            )
        fields_clean[str(k)] = fv

    k1 = float(bm25_raw.get("k1", 1.5))
    b = float(bm25_raw.get("b", 0.75))
    if k1 <= 0:
        raise ConfigError(f"search.bm25.k1={k1} 必须 >0（业内常用 1.2~2.0）")
    if not (0 <= b <= 1):
        raise ConfigError(f"search.bm25.b={b} 必须在 [0,1]（业内常用 0.75）")
    default_limit = int(bm25_raw.get("default_limit", 10))
    if default_limit <= 0:
        raise ConfigError(f"search.bm25.default_limit={default_limit} 必须 >0")
    bm25_cfg = BM25SearchConfig(
        enabled=bool(bm25_raw.get("enabled", True)),
        k1=k1,
        b=b,
        default_limit=default_limit,
        fields=fields_clean,
    )

    hybrid_raw = raw.get("hybrid") or {}
    if not isinstance(hybrid_raw, dict):
        raise ConfigError("search.hybrid 必须是 YAML 对象")
    weights_raw = hybrid_raw.get("weights") or {}
    if not isinstance(weights_raw, dict):
        raise ConfigError("search.hybrid.weights 必须是 YAML 对象")
    weights_clean: dict[str, float] = {}
    for k, v in weights_raw.items():
        try:
            fv = float(v)
        except (TypeError, ValueError) as e:
            raise ConfigError(
                f"search.hybrid.weights.{k}={v!r} 必须是数值"
            ) from e
        if fv < 0:
            raise ConfigError(f"search.hybrid.weights.{k}={fv} 必须 >=0")
        weights_clean[str(k)] = fv
    if not weights_clean:
        weights_clean = {"bm25": 0.75, "value_score": 0.15, "review_due": 0.10}
    hybrid_cfg = HybridSearchConfig(
        enabled=bool(hybrid_raw.get("enabled", True)),
        weights=weights_clean,
    )
    return SearchConfig(bm25=bm25_cfg, hybrid=hybrid_cfg)


def _parse_llm(raw: dict[str, Any]) -> LLMConfig:
    active_profile = _require(raw, "active_profile", str, ctx="llm")
    profiles_raw = _require(raw, "profiles", dict, ctx="llm")
    models_raw = _require(raw, "models", dict, ctx="llm")

    if active_profile not in profiles_raw:
        raise ConfigError(
            f"llm.active_profile={active_profile!r} 在 llm.profiles 中不存在"
        )

    # 解析 models
    models: dict[str, ModelConfig] = {}
    for alias, mraw in models_raw.items():
        if not isinstance(mraw, dict):
            raise ConfigError(f"llm.models.{alias} 必须是 YAML 对象")
        # base_url 与 base_url_env 至少一个必须存在；fake 类型例外
        base_url_env = mraw.get("base_url_env")
        if "base_url" in mraw:
            base_url = str(mraw["base_url"])
        elif base_url_env:
            base_url = ""  # 运行时由 provider 从 env 读取
        elif mraw.get("type") == "fake":
            base_url = "fake://"
        else:
            raise ConfigError(
                f"llm.models.{alias} 必须提供 base_url 或 base_url_env 之一"
            )
        # model 与 model_env 至少一个有效（model_env 仅在运行时由 provider 解析）
        model_env = mraw.get("model_env")
        model_str = mraw.get("model")
        if not model_str and not model_env:
            raise ConfigError(
                f"llm.models.{alias} 必须提供 model 或 model_env 之一"
            )
        models[alias] = ModelConfig(
            alias=alias,
            provider=_require(mraw, "provider", str, ctx=f"llm.models.{alias}"),
            type=_require(mraw, "type", str, ctx=f"llm.models.{alias}"),
            base_url=base_url,
            model=str(model_str or ""),
            timeout_seconds=int(mraw.get("timeout_seconds", 120)),
            max_retries=int(mraw.get("max_retries", 1)),
            api_key_env=mraw.get("api_key_env"),
            api_key_optional=bool(mraw.get("api_key_optional", False)),
            base_url_env=base_url_env,
            version_env=mraw.get("version_env"),
            model_env=model_env,
        )

    # 校验每个 profile：必须覆盖全部 5 个 stage，且 alias 必须存在
    profiles: dict[str, dict[str, str]] = {}
    for pname, pmap in profiles_raw.items():
        if not isinstance(pmap, dict):
            raise ConfigError(f"llm.profiles.{pname} 必须是 YAML 对象")
        missing = [s for s in REQUIRED_STAGES if s not in pmap]
        if missing:
            raise ConfigError(
                f"llm.profiles.{pname} 缺少 stage 映射：{missing}；"
                f"v0.1 必须覆盖 {list(REQUIRED_STAGES)}"
            )
        for stage, alias in pmap.items():
            if alias not in models:
                raise ConfigError(
                    f"llm.profiles.{pname}.{stage}={alias!r} 不在 llm.models 中"
                )
        profiles[pname] = dict(pmap)

    # active_profile 是否需要 api_key？仅检查 active_profile 涉及的 model
    active_aliases = set(profiles[active_profile].values())
    for alias in active_aliases:
        m = models[alias]
        if m.api_key_env and not m.api_key_optional:
            # 不强制现在就读环境变量（开发阶段可能没设），仅记录契约要求
            pass

    return LLMConfig(active_profile=active_profile, profiles=profiles, models=models)


def load_learning_tracks(path: str | Path) -> LearningTracksConfig:
    """加载并校验 learning_tracks.yaml。"""
    p = Path(path)
    raw = _read_yaml(p)
    tracks_raw = _require(raw, "tracks", list, ctx=str(p))

    tracks: list[TrackConfig] = []
    seen_ids: set[str] = set()
    for i, t in enumerate(tracks_raw):
        if not isinstance(t, dict):
            raise ConfigError(f"learning_tracks.tracks[{i}] 必须是 YAML 对象")
        tid = _require(t, "id", str, ctx=f"tracks[{i}]")
        if tid in seen_ids:
            raise ConfigError(f"learning_tracks 中存在重复 id：{tid!r}")
        seen_ids.add(tid)
        tracks.append(
            TrackConfig(
                id=tid,
                keywords=tuple(t.get("keywords") or []),
                negative_keywords=tuple(t.get("negative_keywords") or []),
                output_focus=tuple(t.get("output_focus") or []),
            )
        )

    return LearningTracksConfig(version=int(raw.get("version", 1)), tracks=tuple(tracks))


def _require(d: dict[str, Any], key: str, expected_type: type, *, ctx: str) -> Any:
    if key not in d:
        raise ConfigError(f"{ctx}: 缺少必填字段 {key!r}")
    val = d[key]
    if expected_type is int:
        # YAML 里 int 也可能被解析成 bool 的子类；这里宽松处理
        if isinstance(val, bool) or not isinstance(val, int):
            raise ConfigError(f"{ctx}.{key} 必须是 int，得到 {type(val).__name__}")
    elif not isinstance(val, expected_type):
        raise ConfigError(
            f"{ctx}.{key} 必须是 {expected_type.__name__}，得到 {type(val).__name__}"
        )
    return val


__all__ = [
    "REQUIRED_STAGES",
    "KNOWN_SOURCE_TYPES",
    "ConfigError",
    "VaultConfig",
    "SourceRegistryEntry",
    "SourcesConfig",
    "StateConfig",
    "TriageConfig",
    "ReviewConfig",
    "ReviewIntervals",
    "TelemetryConfig",
    "BM25SearchConfig",
    "HybridSearchConfig",
    "SearchConfig",
    "ModelConfig",
    "LLMConfig",
    "PromptVersions",
    "LoggingConfig",
    "MindForgeConfig",
    "TrackConfig",
    "LearningTracksConfig",
    "load_mindforge_config",
    "load_learning_tracks",
]
