"""Model setup readiness for first-run CLI surfaces.

中文学习型说明：first-run 的 ``init/start/doctor/status`` 都是 read path。
它们需要回答“现在能不能跑需要模型的 background processing”，但不能读取
secret value、不能调用 LLM、也不能把 env/profile/fake 重新暴露成产品语义。
本模块只做 metadata + local secret presence 判断，作为 CLI 统一边界。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import REQUIRED_STAGES, MindForgeConfig, ModelConfig
from .secret_store import SecretStore, find_secret_store_path, resolve_project_root_from_config


@dataclass(frozen=True)
class ModelSetupReadiness:
    status: str
    label: str
    model_count: int
    missing_model_ids: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.status == "ready"


def model_setup_readiness(cfg: MindForgeConfig) -> ModelSetupReadiness:
    """Return secret-safe readiness for source processing.

    判定边界：
    - 必须有 default/routing 能覆盖 REQUIRED_STAGES；
    - 每个涉及的真实模型必须有 base_url/model metadata；
    - 非 optional API key 必须在 local secret store 中存在；
    - 不读取 raw key value，不调用 provider，不检查网络。
    """

    if not cfg.llm.models:
        return ModelSetupReadiness("needs_setup", "needs setup", 0, ())
    model_ids = _required_model_ids(cfg)
    if not model_ids:
        return ModelSetupReadiness("needs_setup", "needs setup", len(cfg.llm.models), ())

    store = SecretStore(_secret_store_path(cfg))
    missing: list[str] = []
    for model_id in sorted(model_ids):
        model = cfg.llm.models.get(model_id)
        if model is None or not _model_metadata_complete(model):
            missing.append(model_id)
            continue
        if model.type != "fake" and not model.api_key_optional and not store.present(model_id):
            missing.append(model_id)
    if missing:
        return ModelSetupReadiness(
            "needs_setup",
            "needs setup",
            len(cfg.llm.models),
            tuple(missing),
        )
    return ModelSetupReadiness("ready", "ready", len(cfg.llm.models), ())


def _required_model_ids(cfg: MindForgeConfig) -> set[str]:
    routing = cfg.llm.routing or {}
    model_ids = {routing[stage] for stage in REQUIRED_STAGES if stage in routing}
    if not model_ids and cfg.llm.default_model:
        model_ids.add(cfg.llm.default_model)
    return model_ids


def _model_metadata_complete(model: ModelConfig) -> bool:
    if model.type not in {"fake", "openai"} and not (model.base_url or model.base_url_env):
        return False
    return bool(model.model or model.model_env)


def _secret_store_path(cfg: MindForgeConfig) -> Path:
    """解析 secrets.json 路径，复用 ``find_secret_store_path`` 的锚点语义。

    与 processing provider 使用同一套 project_root → secrets path 解析逻辑。
    当 project_root 已解析但 secrets 文件尚未创建（用户未做 Web Setup）时，
    返回 project_root 锚定的预期路径，而非 CWD 任意位置。这样 readiness 判断
    与 processing provider 始终校验同一 workspace 的 secrets。
    """
    project_root = resolve_project_root_from_config(cfg)
    result = find_secret_store_path(project_root=project_root)
    if result is not None:
        return result
    if project_root is not None:
        return project_root / ".mindforge" / "secrets.json"
    return Path.cwd() / ".mindforge" / "secrets.json"


__all__ = ["ModelSetupReadiness", "model_setup_readiness"]
