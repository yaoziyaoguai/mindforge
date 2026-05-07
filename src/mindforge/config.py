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

from .assets_runtime import bundled_text

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
        "cubox_api",
        "plain_markdown",
        "webclip_markdown",
        "pdf",
        "docx",
        "chat_export",
        "manual_note",
        "obsidian_note",
        "common_document",
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

    复习字段属于本地 review 子系统；当前实现导览见 README.md。"""

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
    default_model: str | None = None
    routing: dict[str, str] = field(default_factory=dict)
    legacy_config_detected: bool = False

    def resolve_stage(self, stage: str) -> ModelConfig:
        """按当前 active_profile 把 stage 解析为 ModelConfig。"""
        profile = self.profiles[self.active_profile]
        alias = profile[stage]
        return self.models[alias]


def with_fake_llm_profile(llm: LLMConfig) -> LLMConfig:
    """为 legacy/dev-only 离线路径临时注入 fake profile。

    中文学习型说明：用户默认配置和 package defaults 不再暴露 fake/profile 语义；
    但老的 smoke、preview 和 ``--profile fake`` 仍需要 deterministic 本地替身。
    这里在内存中派生 fake profile，不写回 YAML，也不污染 Setup 主 UI。
    """

    fake_models = {
        "fake_fast": ModelConfig(
            alias="fake_fast",
            provider="fake",
            type="fake",
            base_url="fake://",
            model="fake-fast",
            timeout_seconds=5,
            max_retries=0,
        ),
        "fake_strong": ModelConfig(
            alias="fake_strong",
            provider="fake",
            type="fake",
            base_url="fake://",
            model="fake-strong",
            timeout_seconds=5,
            max_retries=0,
        ),
    }
    return LLMConfig(
        active_profile="fake",
        profiles={
            **llm.profiles,
            "fake": {
                "triage": "fake_fast",
                "distill": "fake_strong",
                "link_suggestion": "fake_fast",
                "review_questions": "fake_strong",
                "action_extraction": "fake_strong",
            },
        },
        models={**llm.models, **fake_models},
        default_model=llm.default_model,
        routing=dict(llm.routing),
        legacy_config_detected=llm.legacy_config_detected,
    )


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
    """本地 telemetry 子配置（边界见 README.md）。

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
class StrategyConfig:
    """知识抽取策略配置。

    中文学习型说明：provider selection 与 strategy selection 是两条正交轴。
    ``llm.active`` 决定“用哪个 provider/model”，``strategy.active`` 决定
    “用哪种知识抽取/卡片组织方式”。配置层只记录用户意图；是否可执行由
    strategy registry 在运行边界验证，避免 config.py 反向依赖 runtime。
    """

    active: str = "knowledge_card"


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
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
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


def _load_internal_defaults() -> dict[str, Any]:
    """读取 package 内置 full config defaults。

    中文学习型说明：新用户的 ``configs/mindforge.yaml`` 是 override，不再承担
    sources/state/search/prompts 等系统默认细节。这里把 internal full config
    作为运行时默认值，再让用户 YAML 覆盖它；CLI/provider/ingestion 不需要
    知道这层合并存在。
    """

    try:
        data = yaml.safe_load(bundled_text("configs", "mindforge.yaml"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"内置 mindforge defaults YAML 解析失败: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("内置 mindforge defaults 顶层必须是 YAML 对象")
    return data


def _deep_merge_defaults(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """递归合并 config：dict 合并，scalar/list 由用户 override 覆盖。"""

    merged = dict(defaults)
    for key, value in overrides.items():
        default_value = merged.get(key)
        if isinstance(default_value, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_defaults(default_value, value)
        else:
            merged[key] = value
    return merged


def _merge_user_config_with_defaults(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """合并用户配置，同时保护 LLM 用户语义不被另一种格式污染。

    中文学习型说明：package defaults 使用新的 ``models/default_model/routing``。
    用户配置如果也是新格式，就不能深合并出其它 model id；用户配置如果是
    legacy ``active_profile/profiles`` 或过渡期 ``active/providers``，也不能让
    defaults 里的 ``default_model`` 抢先把它解析成新格式。
    """

    if not isinstance(overrides.get("llm"), dict):
        return _deep_merge_defaults(defaults, overrides)
    user_llm = overrides["llm"]
    if "default_model" not in user_llm and not _is_legacy_llm_override(user_llm):
        return _deep_merge_defaults(defaults, overrides)

    overrides_without_llm = dict(overrides)
    overrides_without_llm.pop("llm")
    merged = _deep_merge_defaults(defaults, overrides_without_llm)
    merged["llm"] = dict(user_llm)
    return merged


def _is_legacy_llm_override(llm: dict[str, Any]) -> bool:
    return any(key in llm for key in ("active", "active_profile", "providers", "profiles"))


def _expand_user_profile_overrides(raw: dict[str, Any]) -> dict[str, Any]:
    """把用户层 provider 选择映射成 internal stage/model 结构。

    新用户 YAML 使用 ``llm.active`` + ``llm.providers``；旧配置仍可能使用
    ``active_profile`` + ``profiles``。完整 pipeline 仍需要五个 stage 的 alias
    映射与 ``llm.models``。本函数在配置层完成兼容翻译，保持
    watch/import/process 的业务管线不感知 provider selection UX 的变化。
    """

    llm = raw.get("llm")
    if not isinstance(llm, dict):
        return raw
    if "default_model" in llm:
        return raw
    providers = llm.get("providers")
    if isinstance(providers, dict):
        active = llm.get("active")
        if not isinstance(active, str) or not active.strip():
            raise ConfigError("llm.active 必须指定 llm.providers 下的 provider key")
        if active not in providers:
            raise ConfigError(
                f"llm.active={active!r} 不在 llm.providers 中；已知：{sorted(providers)}"
            )
        llm["active_profile"] = active
        profiles_from_providers = {
            str(name): _legacy_profile_from_provider(str(name), value)
            for name, value in providers.items()
            if isinstance(value, dict)
        }
        legacy_profiles = llm.get("profiles")
        if isinstance(legacy_profiles, dict):
            for name, value in legacy_profiles.items():
                profiles_from_providers.setdefault(str(name), value)
        llm["profiles"] = profiles_from_providers

    profiles = llm.get("profiles")
    if not isinstance(profiles, dict):
        return raw
    models = llm.setdefault("models", {})
    if not isinstance(models, dict):
        return raw

    _expand_real_provider_profile(
        profiles,
        models,
        profile_name="openai_compatible",
        provider_type="openai_compatible",
        provider_name="openai_compatible",
        alias="openai_strong",
        fallback_base_url="https://api.openai.com/v1",
        fallback_model="gpt-4o-mini",
    )
    _expand_real_provider_profile(
        profiles,
        models,
        profile_name="anthropic",
        provider_type="anthropic_compatible",
        provider_name="anthropic",
        alias="anthropic_strong",
        fallback_base_url="https://api.anthropic.com",
        fallback_model="claude-3-5-haiku-latest",
    )

    fake_profile = profiles.get("fake")
    if (
        isinstance(fake_profile, dict)
        and fake_profile.get("provider") == "fake"
        and not all(stage in fake_profile for stage in REQUIRED_STAGES)
    ):
        fake_profile.update(
            {
                "triage": "fake_fast",
                "distill": "fake_strong",
                "link_suggestion": "fake_fast",
                "review_questions": "fake_strong",
                "action_extraction": "fake_strong",
            }
        )
    if isinstance(fake_profile, dict) and fake_profile.get("provider") == "fake":
        models.setdefault(
            "fake_fast",
            {"provider": "fake", "type": "fake", "model": "fake-fast"},
        )
        models.setdefault(
            "fake_strong",
            {"provider": "fake", "type": "fake", "model": "fake-strong"},
        )
    return raw


def _legacy_profile_from_provider(name: str, provider: dict[str, Any]) -> dict[str, Any]:
    """把新 ``llm.providers`` 项转换成 legacy profile 形状。

    这是配置兼容层，不是业务 provider 路由。生成的 stage 映射会继续交给
    ``_expand_real_provider_profile`` / fake 展开逻辑处理。
    """

    provider_type = str(provider.get("type") or name)
    legacy: dict[str, Any] = dict(provider)
    legacy.pop("type", None)
    legacy["provider"] = provider_type
    if "default_base_url" in legacy:
        legacy["base_url"] = legacy.pop("default_base_url")
    if "default_model" in legacy:
        legacy["model"] = legacy.pop("default_model")
    return legacy


def _expand_real_provider_profile(
    profiles: dict[str, Any],
    models: dict[str, Any],
    *,
    profile_name: str,
    provider_type: str,
    provider_name: str,
    alias: str,
    fallback_base_url: str,
    fallback_model: str,
) -> None:
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        return
    if all(stage in profile for stage in REQUIRED_STAGES):
        return
    if profile.get("provider") != provider_name:
        return

    default_base_url = str(profile.get("default_base_url") or profile.get("base_url") or fallback_base_url)
    default_model = str(profile.get("default_model") or profile.get("model") or fallback_model)
    models[alias] = {
        "provider": provider_name,
        "type": provider_type,
        "base_url": default_base_url,
        "api_key_env": profile.get("api_key_env"),
        "base_url_env": profile.get("base_url_env"),
        "model_env": profile.get("model_env"),
        "model": default_model,
        "timeout_seconds": int(profile.get("timeout_seconds") or 120),
        "max_retries": int(profile.get("max_retries") or 2),
    }
    profile.update({stage: alias for stage in REQUIRED_STAGES})


def _parse_vault(raw: dict[str, Any], *, ctx: str) -> VaultConfig:
    vault_raw = _require(raw, "vault", dict, ctx=ctx)
    root = Path(_require(vault_raw, "root", str, ctx="vault")).expanduser()
    config_meta = raw.get("_mindforge_config")
    project_root = None
    if isinstance(config_meta, dict) and config_meta.get("project_root"):
        project_root = Path(str(config_meta["project_root"])).expanduser()
    if not root.is_absolute() and project_root is not None:
        root = project_root / root
    return VaultConfig(
        root=root.resolve(),
        inbox_root=_require(vault_raw, "inbox_root", str, ctx="vault"),
        cards_dir=_require(vault_raw, "cards_dir", str, ctx="vault"),
        archive_dir=_require(vault_raw, "archive_dir", str, ctx="vault"),
        projects_dir=str(vault_raw.get("projects_dir") or "30-Projects"),
    )


def _parse_sources(raw: dict[str, Any], *, ctx: str) -> SourcesConfig:
    sources_raw = _require(raw, "sources", dict, ctx=ctx)
    enabled_list = _require(sources_raw, "enabled", list, ctx="sources")
    registry_raw = _require(sources_raw, "registry", dict, ctx="sources")

    registry: dict[str, SourceRegistryEntry] = {}
    for source_type, entry in registry_raw.items():
        if source_type not in KNOWN_SOURCE_TYPES:
            raise ConfigError(
                f"sources.registry 出现未知 source_type {source_type!r}；"
                f"已知集合：{sorted(KNOWN_SOURCE_TYPES)}"
            )
        if not isinstance(entry, dict):
            raise ConfigError(f"sources.registry.{source_type} 必须是 YAML 对象")
        registry[source_type] = SourceRegistryEntry(
            source_type=source_type,
            adapter=_require(entry, "adapter", str, ctx=f"sources.registry.{source_type}"),
            inbox_subdir=_require(entry, "inbox_subdir", str, ctx=f"sources.registry.{source_type}"),
            file_glob=_require(entry, "file_glob", str, ctx=f"sources.registry.{source_type}"),
            # enabled 字段在 v0.1 默认 True；显式 false 表示占位 stub。
            enabled=bool(entry.get("enabled", True)),
        )
    for source_type in enabled_list:
        if source_type not in registry:
            raise ConfigError(
                f"sources.enabled 列出的 {source_type!r} 不在 sources.registry 中"
            )
    return SourcesConfig(enabled=tuple(enabled_list), registry=registry)


def _parse_state(raw: dict[str, Any], *, ctx: str, base_dir: Path) -> StateConfig:
    state_raw = _require(raw, "state", dict, ctx=ctx)
    workdir_str = _require(state_raw, "workdir", str, ctx="state")
    workdir = Path(workdir_str)
    return StateConfig(
        workdir=(base_dir / workdir_str) if not workdir.is_absolute() else workdir,
        state_file=_require(state_raw, "state_file", str, ctx="state"),
        runs_dir=_require(state_raw, "runs_dir", str, ctx="state"),
        index_file=_require(state_raw, "index_file", str, ctx="state"),
        backup_state=bool(state_raw.get("backup_state", True)),
    )


def _parse_triage(raw: dict[str, Any], *, ctx: str) -> TriageConfig:
    triage_raw = _require(raw, "triage", dict, ctx=ctx)
    return TriageConfig(
        value_score_threshold=int(_require(triage_raw, "value_score_threshold", int, ctx="triage")),
        default_track=_require(triage_raw, "default_track", str, ctx="triage"),
    )


def _parse_prompts(raw: dict[str, Any], *, ctx: str) -> PromptVersions:
    prompts_raw = _require(raw, "prompts", dict, ctx=ctx)
    return PromptVersions(
        triage=_require(prompts_raw, "triage_version", str, ctx="prompts"),
        distill=_require(prompts_raw, "distill_version", str, ctx="prompts"),
        link_suggestion=_require(prompts_raw, "link_suggestion_version", str, ctx="prompts"),
        review_questions=_require(prompts_raw, "review_questions_version", str, ctx="prompts"),
        action_extraction=_require(prompts_raw, "action_extraction_version", str, ctx="prompts"),
    )


def _parse_logging(raw: dict[str, Any], *, ctx: str) -> LoggingConfig:
    logging_raw = _require(raw, "logging", dict, ctx=ctx)
    return LoggingConfig(
        level=str(logging_raw.get("level", "INFO")),
        file=str(logging_raw.get("file", ".mindforge/mindforge.log")),
        record_prompts=bool(logging_raw.get("record_prompts", True)),
        record_outputs=bool(logging_raw.get("record_outputs", True)),
    )


def _parse_review(raw: dict[str, Any]) -> ReviewConfig:
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
    for name, value in (
        ("remembered", intervals.remembered),
        ("partial", intervals.partial),
        ("forgotten", intervals.forgotten),
    ):
        if value < 0:
            raise ConfigError(f"review.intervals.{name} 必须 >=0，得到 {value}")
    return ReviewConfig(
        intervals=intervals,
        default_include_drafts=bool(review_raw.get("default_include_drafts", False)),
    )


def _parse_telemetry(raw: dict[str, Any]) -> TelemetryConfig:
    telemetry_raw = raw.get("telemetry") or {}
    if not isinstance(telemetry_raw, dict):
        raise ConfigError(
            f"telemetry 必须是 mapping，得到 {type(telemetry_raw).__name__}"
        )
    return TelemetryConfig(
        enabled=bool(telemetry_raw.get("enabled", True)),
        local_only=bool(telemetry_raw.get("local_only", True)),
    )


def load_mindforge_config(path: str | Path) -> MindForgeConfig:
    """加载并校验 mindforge.yaml，返回不可变快照。

    中文学习型说明：相对 ``state.workdir`` 按当前工作目录解析，而不是按
    config 文件父目录猜测仓库根。packaged install 下 config 可能被复制到任意
    位置，继续使用 ``config.parent.parent`` 会把 `.mindforge` 写到违背直觉
    的目录，甚至写到系统根附近。显式绝对路径仍保持原样。
    """
    p = Path(path)
    user_raw = _read_yaml(p)
    if not any(key in user_raw for key in ("version", "vault", "llm", "telemetry")):
        raise ConfigError(
            f"{p}: 不是有效的 MindForge 配置；至少需要 version/vault/llm/telemetry 之一"
        )
    raw = _expand_user_profile_overrides(
        _merge_user_config_with_defaults(_load_internal_defaults(), user_raw)
    )
    config_path = p.expanduser().resolve()
    project_root = _project_root_for_config(config_path)
    raw["_mindforge_config"] = {
        "path": str(config_path),
        "project_root": str(project_root),
    }
    base_dir = Path.cwd()
    ctx = str(p)

    vault = _parse_vault(raw, ctx=ctx)
    sources = _parse_sources(raw, ctx=ctx)
    state = _parse_state(raw, ctx=ctx, base_dir=base_dir)
    triage = _parse_triage(raw, ctx=ctx)
    llm = _parse_llm(_require(raw, "llm", dict, ctx=str(p)))
    prompts = _parse_prompts(raw, ctx=ctx)
    logging_cfg = _parse_logging(raw, ctx=ctx)
    review_cfg = _parse_review(raw)
    telemetry_cfg = _parse_telemetry(raw)
    obsidian_cfg = _parse_obsidian(raw.get("obsidian") or {})
    search_cfg = _parse_search(raw.get("search") or {})
    strategy_cfg = _parse_strategy(raw.get("strategy") or {})

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
        strategy=strategy_cfg,
        raw=raw,
    )


def _parse_strategy(raw: Any) -> StrategyConfig:
    """解析 ``strategy.active``，缺失时稳定回退 knowledge_card。

    中文学习型说明：这里不校验 strategy 是否存在/可执行。那属于 registry
    运行边界；如果在 config 层 import registry，会让纯配置 loader 意外承担
    strategy runtime 知识，也会让错误来源不清晰。
    """

    if not isinstance(raw, dict):
        raise ConfigError(f"strategy 必须是 YAML 对象，得到 {type(raw).__name__}")
    active = str(raw.get("active") or "knowledge_card").strip()
    if not active:
        raise ConfigError("strategy.active 不能为空")
    return StrategyConfig(active=active)


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


def _project_root_for_config(config_path: Path) -> Path:
    """从 config path 推导 project root。

    中文学习型说明：新用户配置是 project-local override，``vault.root: vault``
    这类相对路径必须稳定地按 project root 解析。标准路径
    ``<project>/configs/mindforge.yaml`` 的 project root 是 ``<project>``；
    其它显式 config path 则退回到 config 文件所在目录，保持旧配置兼容。
    """

    if config_path.name == "mindforge.yaml" and config_path.parent.name == "configs":
        return config_path.parent.parent
    return config_path.parent


def _parse_llm(raw: dict[str, Any]) -> LLMConfig:
    if "default_model" in raw:
        return _parse_model_routing_llm(raw)

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
            if stage not in REQUIRED_STAGES:
                continue
            if alias not in models:
                raise ConfigError(
                    f"llm.profiles.{pname}.{stage}={alias!r} 不在 llm.models 中"
                )
        profiles[pname] = {stage: str(pmap[stage]) for stage in REQUIRED_STAGES}

    # active_profile 是否需要 api_key？仅检查 active_profile 涉及的 model
    active_aliases = set(profiles[active_profile].values())
    for alias in active_aliases:
        m = models[alias]
        if m.api_key_env and not m.api_key_optional:
            # 不强制现在就读环境变量（开发阶段可能没设），仅记录契约要求
            pass

    return LLMConfig(
        active_profile=active_profile,
        profiles=profiles,
        models=models,
        default_model=None,
        routing=dict(profiles[active_profile]),
        legacy_config_detected=True,
    )


def _parse_model_routing_llm(raw: dict[str, Any]) -> LLMConfig:
    """解析用户可见的新 LLM 语义，并生成现有执行层可消费的 routing plan。

    ``LLMClient`` / provider factory 当前仍消费 ``active_profile/profiles``。
    这里把新格式转换成单个内部 profile，保持执行链稳定；对用户和 Setup 暴露
    的 source of truth 仍是 ``default_model/models/routing``。
    """

    default_model = _require(raw, "default_model", str, ctx="llm")
    models_raw = _require(raw, "models", dict, ctx="llm")
    if default_model not in models_raw:
        raise ConfigError(
            f"llm.default_model={default_model!r} 不在 llm.models 中；"
            f"已知：{sorted(models_raw)}"
        )

    models = _parse_llm_models(models_raw)
    routing_raw = raw.get("routing") or {}
    if not isinstance(routing_raw, dict):
        raise ConfigError(
            f"llm.routing 必须是 YAML 对象，得到 {type(routing_raw).__name__}"
        )
    routing: dict[str, str] = {}
    for stage in REQUIRED_STAGES:
        value = routing_raw.get(stage, default_model)
        if not isinstance(value, str):
            raise ConfigError(f"llm.routing.{stage} 必须是 model id 字符串")
        if value not in models:
            raise ConfigError(
                f"llm.routing.{stage}={value!r} 不在 llm.models 中；"
                f"已知：{sorted(models)}"
            )
        routing[stage] = value
    for stage in routing_raw:
        if stage not in REQUIRED_STAGES:
            raise ConfigError(
                f"llm.routing 出现未知 workflow step {stage!r}；"
                f"已知：{list(REQUIRED_STAGES)}"
            )

    active_profile = "__model_routing__"
    return LLMConfig(
        active_profile=active_profile,
        profiles={active_profile: dict(routing)},
        models=models,
        default_model=default_model,
        routing=dict(routing),
        legacy_config_detected=False,
    )


def _parse_llm_models(models_raw: dict[str, Any]) -> dict[str, ModelConfig]:
    models: dict[str, ModelConfig] = {}
    for model_id, mraw in models_raw.items():
        if not isinstance(mraw, dict):
            raise ConfigError(f"llm.models.{model_id} 必须是 YAML 对象")
        models[str(model_id)] = _parse_llm_model(str(model_id), mraw)
    return models


def _parse_llm_model(model_id: str, mraw: dict[str, Any]) -> ModelConfig:
    if "type" not in mraw:
        raise ConfigError(
            f"llm.models.{model_id}.type 缺失；必须显式配置为 "
            "anthropic, anthropic_compatible 或 openai_compatible，不能从 base_url/model 自动猜协议"
        )
    model_type = _require(mraw, "type", str, ctx=f"llm.models.{model_id}")
    if model_type not in {"anthropic", "anthropic_compatible", "openai_compatible", "fake"}:
        raise ConfigError(
            f"llm.models.{model_id}.type={model_type!r} 不支持；"
            "支持：anthropic, anthropic_compatible, openai_compatible"
        )

    base_url_env = mraw.get("base_url_env")
    if "base_url" in mraw:
        base_url = str(mraw["base_url"])
    elif base_url_env:
        base_url = ""
    elif model_type == "fake":
        base_url = "fake://"
    else:
        raise ConfigError(
            f"llm.models.{model_id} 必须提供 base_url 或 base_url_env 之一"
        )

    model_env = mraw.get("model_env")
    model_str = mraw.get("model")
    if not model_str and not model_env:
        raise ConfigError(
            f"llm.models.{model_id} 必须提供 model 或 model_env 之一"
        )

    return ModelConfig(
        alias=model_id,
        provider=str(mraw.get("provider") or model_id),
        type=model_type,
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
