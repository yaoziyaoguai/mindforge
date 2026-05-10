"""Secret-safe Web configuration status.

中文学习型说明：Web 需要告诉用户“哪些 key 已配置”，但绝不能泄露 key 的值。
因此本模块只做 `.env` 文件的 key presence 解析，并且不把 value 写入
`os.environ`。provider readiness 仍复用 `mindforge.provider_readiness`。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mindforge.config import REQUIRED_STAGES, MindForgeConfig
from mindforge.cubox_readiness import classify_cubox_real_opt_in, inspect_cubox_config
from mindforge.provider_readiness import build_readiness_report
from mindforge.watch_registry import list_watch_sources, registry_path_for_vault

from mindforge_web.schemas import (
    EditableCuboxConfig,
    EditableLLMConfig,
    EditableModelConfig,
    EditableProviderConfig,
    EditableVaultConfig,
    EditableWikiConfig,
    EnvKeyStatus,
    NextAction,
    ProcessingWorkflowConfig,
    ProcessingWorkflowStep,
    ProviderAliasStatus,
    ProviderStatus,
    ResolvedWorkflowModelConfig,
    SetupConfigPatch,
    SetupEditableConfigResponse,
    SetupValidationResponse,
    StatusItem,
)
from mindforge.secret_store import SecretStore


@dataclass(frozen=True)
class DotenvPresence:
    path: Path | None
    keys: frozenset[str]


class WebConfigService:
    """配置状态读取边界；只返回 secret-safe metadata。"""

    def __init__(
        self,
        cfg: MindForgeConfig,
        *,
        config_path: Path,
        cwd: Path | None = None,
    ) -> None:
        self.cfg = cfg
        self.config_path = config_path
        self.cwd = cwd or Path.cwd()
        # .mindforge/ 目录在项目根（configs/ 的父目录）
        # 中文学习型说明：不再 fallback 到 cwd。标准结构 <project>/configs/mindforge.yaml
        # 的 project root 是 <project>；扁平结构 <dir>/mindforge.yaml 的 project root
        # 是 <dir>。自动创建 .mindforge/，避免 secret store 写到错误目录。
        config_dir = config_path.resolve().parent
        if config_dir.name == "configs":
            project_root = config_dir.parent
        else:
            project_root = config_dir
        mindforge_dir = project_root / ".mindforge"
        mindforge_dir.mkdir(parents=True, exist_ok=True)
        self.secrets = SecretStore(mindforge_dir / "secrets.json")

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

    def editable_config(self) -> SetupEditableConfigResponse:
        """返回 Setup editor 可编辑视图；只包含非敏感字段与 secret presence。"""

        raw = self._read_config_raw()
        cubox_export, cubox_import = _cubox_paths(raw)
        watched_count = len([
            source
            for source in list_watch_sources(
                self.cfg.vault.root,
                registry_path_for_vault(self.cfg.vault.root),
            )
            if not source.is_default
        ])
        return SetupEditableConfigResponse(
            config_path=str(self.config_path),
            normalized_on_save=True,
            vault=EditableVaultConfig(
                root=str(self.cfg.vault.root),
                exists=self.cfg.vault.root.exists(),
                inbox_exists=self.cfg.vault.inbox_path.exists(),
                cards_exists=self.cfg.vault.cards_path.exists(),
                projects_exists=self.cfg.vault.projects_path.exists(),
            ),
            llm=EditableLLMConfig(
                active_provider=self.cfg.llm.active_profile,
                available_providers=self._configured_provider_names(raw),
                providers=self._editable_providers(raw),
                readiness=self.provider_status(),
                configured_model_ids=self._configured_model_ids(raw),
                configured_models=self._editable_models(raw),
                default_model=self._editable_default_model(raw),
                routing=self._editable_routing(raw),
                routing_is_explicit=self._routing_is_explicit(raw),
                resolved_per_step_models=self._resolved_per_step_models(raw),
                processing_workflow=self._workflow_config(raw),
                legacy_config_detected=self._legacy_config_detected(raw),
                validation_errors=self._llm_validation_errors(raw),
                warnings=self._llm_warnings(raw),
            ),
            wiki=EditableWikiConfig(
                mode=self.cfg.wiki.mode if hasattr(self.cfg, 'wiki') else "deterministic",
                model=self.cfg.wiki.model if hasattr(self.cfg, 'wiki') else None,
                auto_rebuild_on_approve=self.cfg.wiki.auto_rebuild_on_approve if hasattr(self.cfg, 'wiki') else False,
            ),
            cubox=EditableCuboxConfig(
                export_path=cubox_export,
                import_path=cubox_import,
                token_status="present"
                if any(item.name == "MINDFORGE_CUBOX_TOKEN" and item.configured for item in self.env_key_statuses())
                else "missing",
            ),
            watch_summary=StatusItem(
                key="watched_sources",
                label="Watched sources",
                status="info",
                value=str(watched_count),
                detail="Setup 展示同一份 watch 状态入口，不维护第二套 watch 配置。",
                next_action=NextAction(
                    label="Open Sources",
                    description="管理 watched source 与一次性 import。",
                    href="/sources",
                ),
            ),
        )

    def validate_patch(self, patch: SetupConfigPatch) -> SetupValidationResponse:
        raw = self._read_config_raw()
        errors: list[str] = []
        warnings: list[str] = []

        if patch.vault_root is not None:
            vault = Path(patch.vault_root).expanduser()
            try:
                resolved = vault.resolve(strict=False)
            except OSError as exc:
                errors.append(f"Vault path cannot be resolved: {exc}")
            else:
                if _is_dangerous_vault_path(resolved):
                    errors.append(f"Vault path is dangerous and cannot be used: {resolved}")
                elif not resolved.exists():
                    warnings.append("Vault directory will be created automatically on save.")
                elif resolved.exists() and not resolved.is_dir():
                    errors.append("Vault path must be a directory.")

        if patch.active_provider is not None and patch.active_provider not in self._configured_provider_names(raw):
            errors.append(
                f"Active provider {patch.active_provider!r} is not configured."
            )

        # 被删除的 model 不能仍被 default_model 或 routing 引用
        deleted = self._deleted_model_ids(raw, patch)
        after_models = self._model_ids_after_patch(raw, patch)
        effective_default = patch.default_model or raw.get("llm", {}).get("default_model")
        if deleted and effective_default in deleted:
            errors.append(
                f"Cannot delete model {effective_default!r}: it is the default_model. "
                f"Change default_model before deleting."
            )

        if patch.default_model and patch.default_model not in after_models:
            errors.append(
                f"Default model {patch.default_model!r} is not in configured models: {sorted(after_models)}"
            )
        # routing 检查：patch 中的 routing 和 raw 中已有的 routing 都不能引用被删除的 model
        effective_routing: dict[str, str] = {}
        existing_routing = raw.get("llm", {}).get("routing")
        if isinstance(existing_routing, dict):
            effective_routing.update(existing_routing)
        if patch.routing:
            effective_routing.update(patch.routing)
        for stage, model_id in effective_routing.items():
            if model_id in deleted:
                errors.append(
                    f"Routing.{stage}={model_id!r} references a model that would be deleted."
                    f" Update routing before deleting {model_id!r}."
                )
            elif model_id not in after_models:
                errors.append(f"Routing model {model_id!r} for {stage} is not configured.")

        for provider, provider_patch in patch.providers.items():
            if provider not in self._configured_provider_names(raw):
                errors.append(f"Provider {provider!r} is not configured.")
            for field_name in ("api_key_env", "base_url_env", "model_env"):
                value = getattr(provider_patch, field_name)
                if value is not None and value.strip() and not value.strip().isidentifier():
                    errors.append(f"{provider}.{field_name} must be an env var name.")

        if patch.cubox_export_path or patch.cubox_import_path:
            warnings.append(
                "Cubox is optional help text only in Setup; add its export folder as a watched source."
            )

        return SetupValidationResponse(ok=not errors, errors=errors, warnings=warnings)

    def _model_ids_after_patch(
        self,
        raw: dict[str, Any],
        patch: SetupConfigPatch,
    ) -> set[str]:
        """计算 patch 应用后的 model id 集合。"""
        if patch.models:
            return set(patch.models.keys())
        return self._all_model_ids(raw)

    def update_patch(self, patch: SetupConfigPatch) -> None:
        validation = self.validate_patch(patch)
        if not validation.ok:
            raise ConfigUpdateError(validation.errors)

        raw = self._read_config_raw()
        if patch.vault_root is not None:
            resolved = Path(patch.vault_root).expanduser().resolve(strict=False)
            # 中文学习型说明：Vault 目录是 first-run 工作区的一部分，不是用户在
            # Setup 主路径里需要理解的内部开关。保存模型时如果目录还不存在，
            # Web 自动创建标准子目录；只有创建失败才返回 friendly error。
            self._create_vault_dirs(resolved)
            vault = raw.setdefault("vault", {})
            if not isinstance(vault, dict):
                raise ConfigUpdateError(["vault must be a YAML object"])
            vault["root"] = str(resolved)

        llm = raw.setdefault("llm", {})
        if not isinstance(llm, dict):
            raise ConfigUpdateError(["llm must be a YAML object"])
        if patch.active_provider is not None:
            if isinstance(llm.get("providers"), dict):
                llm["active"] = patch.active_provider
            else:
                llm["active_profile"] = patch.active_provider

        for provider, provider_patch in patch.providers.items():
            self._apply_provider_patch(raw, provider, provider_patch)

        if patch.default_model is not None or patch.models or patch.routing:
            self._apply_llm_model_routing_patch(raw, patch)
        # Save wiki config
        if any(getattr(patch, f) is not None for f in ("wiki_mode", "wiki_model", "wiki_auto_rebuild_on_approve")):
            wiki = raw.setdefault("wiki", {})
            if patch.wiki_mode is not None:
                wiki["mode"] = patch.wiki_mode
            if patch.wiki_model is not None:
                wiki["model"] = patch.wiki_model if patch.wiki_model else None
            if patch.wiki_auto_rebuild_on_approve is not None:
                wiki["auto_rebuild_on_approve"] = patch.wiki_auto_rebuild_on_approve

        self.config_path.write_text(
            yaml.safe_dump(raw, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
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

    def _read_config_raw(self) -> dict[str, Any]:
        try:
            data = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ConfigUpdateError([f"YAML parse failed: {exc}"]) from exc
        if not isinstance(data, dict):
            raise ConfigUpdateError(["Config file must be a YAML object"])
        return data

    def _available_provider_names(self, raw: dict[str, Any]) -> list[str]:
        llm = raw.get("llm")
        if not isinstance(llm, dict):
            return []
        providers = llm.get("providers")
        if isinstance(providers, dict):
            return sorted(str(name) for name in providers)
        profiles = llm.get("profiles")
        if isinstance(profiles, dict):
            return sorted(str(name) for name in profiles)
        return []

    def _configured_provider_names(self, raw: dict[str, Any]) -> list[str]:
        """返回 Setup 主 UI 可展示的产品 provider。

        中文学习型说明：配置加载层会把 legacy profiles、fallback 和测试替身展开
        成可执行的内部结构；Setup 不能把这些内部路由当作用户可选 provider。
        因此这里仅使用用户 YAML 的 ``llm.providers``。legacy ``profiles``
        是运行时兼容结构，可能来自 registry/default 展开，不能进入主 UI 下拉。
        """

        llm = raw.get("llm")
        if not isinstance(llm, dict):
            return []
        providers = llm.get("providers")
        if isinstance(providers, dict):
            return sorted(
                str(name)
                for name, provider in providers.items()
                if isinstance(provider, dict) and _is_product_provider(str(name), provider.get("type"))
            )
        return []

    def _editable_providers(self, raw: dict[str, Any]) -> dict[str, EditableProviderConfig]:
        providers: dict[str, EditableProviderConfig] = {}
        for name in self._configured_provider_names(raw):
            providers[name] = self._editable_provider(raw, name)
        return providers

    def _configured_model_ids(self, raw: dict[str, Any]) -> list[str]:
        """返回 Setup UI 可展示的模型 id 列表。

        中文学习型说明：普通用户主路径必须配置真实模型。fake/demo/test 模型
        只属于自动化测试或开发内部 fixture，即使 YAML 中存在，也不能作为
        Setup 的产品能力展示出来。
        """
        llm = raw.get("llm")
        if not isinstance(llm, dict) or "default_model" not in llm:
            return []
        models = llm.get("models")
        if not isinstance(models, dict):
            return []
        all_ids = sorted(
            str(model_id)
            for model_id, model_raw in models.items()
            if isinstance(model_raw, dict)
        )
        return [mid for mid in all_ids if _is_product_model(models.get(mid))]

    def _editable_models(self, raw: dict[str, Any]) -> dict[str, EditableModelConfig]:
        llm = raw.get("llm")
        if not isinstance(llm, dict):
            return {}
        models_raw = llm.get("models")
        if not isinstance(models_raw, dict):
            return {}
        models: dict[str, EditableModelConfig] = {}
        for model_id in self._configured_model_ids(raw):
            model_raw = models_raw.get(model_id)
            if isinstance(model_raw, dict):
                models[model_id] = self._editable_model(model_id, model_raw)
        return models

    def _editable_model(self, model_id: str, model_raw: dict[str, Any]) -> EditableModelConfig:
        api_key_env = _str_or_none(model_raw.get("api_key_env"))
        base_url = _str_or_none(model_raw.get("base_url"))
        base_url_env = _str_or_none(model_raw.get("base_url_env"))
        model_value = _str_or_none(model_raw.get("model"))
        model_env = _str_or_none(model_raw.get("model_env"))
        model_type = str(model_raw.get("type") or "")
        effective_base_url, base_url_source = self._effective_non_secret_value(
            env_name=base_url_env,
            default_value=base_url,
        )
        effective_model, model_source = self._effective_non_secret_value(
            env_name=model_env,
            default_value=model_value,
        )
        # API key 来源优先级：local secret store > env var > missing/demo
        api_key_source = self._api_key_source(model_id, model_type, api_key_env)
        api_key_present = api_key_source in ("local_secret", "env")
        masked_value = self._masked_api_key_value(model_id, api_key_env, api_key_source)
        return EditableModelConfig(
            model_id=model_id,
            type=model_type,
            base_url=base_url,
            model=model_value,
            api_key_env=api_key_env,
            api_key_optional=bool(model_raw.get("api_key_optional", False)),
            api_key_status="present" if api_key_present else "missing",
            api_key_env_configured=bool(api_key_env),
            api_key_secret_present=api_key_present,
            api_key_masked_value=masked_value,
            api_key_status_label=_api_key_status_label(api_key_env, api_key_present),
            api_key_source=api_key_source,
            is_demo_model=model_type == "fake",
            base_url_env=base_url_env,
            model_env=model_env,
            effective_base_url=effective_base_url,
            base_url_source=base_url_source,
            effective_model=effective_model,
            model_source=model_source,
        )

    def _editable_default_model(self, raw: dict[str, Any]) -> str | None:
        llm = raw.get("llm")
        if not isinstance(llm, dict):
            return None
        return _str_or_none(llm.get("default_model"))

    def _workflow_config(self, raw: dict[str, Any]) -> ProcessingWorkflowConfig | None:
        """组装 processing workflow 视图 —— 组合 strategy + prompt + model routing。

        中文学习型说明：这个 view 不引入新 config，只把已有 strategy registry、
        prompt versions config、llm.routing/default_model 拼成一份前端可读的
        workflow 描述。React 不自己拼策略逻辑，只消费这个 view。
        """
        from mindforge.strategies.registry import get_strategy_metadata, list_strategies
        from mindforge.strategy_display import strategy_display
        from mindforge.strategy_selection import resolve_strategy_selection

        # 1) 解析 active strategy
        try:
            selection = resolve_strategy_selection(self.cfg)
            active_id = selection.strategy_id
        except Exception:
            active_id = self.cfg.strategy.active if hasattr(self.cfg, 'strategy') else "knowledge_card"

        meta = get_strategy_metadata(active_id)
        sd = strategy_display(active_id)

        # 2) 列出 available strategies（仅 product/implemented）
        available: list[dict] = []
        for s in list_strategies():
            available.append({
                "id": s.strategy_id,
                "label": s.display_name,
                "version": s.strategy_version,
                "status": s.status,
                "description": s.description or "",
            })

        # 3) 组装 workflow steps（固定 5-step，不可自定义 step 数量/顺序）
        step_purposes: dict[str, str] = {
            "triage": "初筛：评估 source 是否值得生成知识卡片，给出 track / value_score",
            "distill": "提炼：从 source 提取核心知识内容，生成卡片草稿主体",
            "link_suggestion": "关联建议：建议可能相关的主题、项目或已有知识链接",
            "review_questions": "复习问题：生成用于后续回忆和自测的问题",
            "action_extraction": "行动项提取：提取可跟进的行动项或待办",
        }
        step_labels: dict[str, str] = {
            "triage": "Triage / 初筛",
            "distill": "Distill / 提炼",
            "link_suggestion": "Link Suggestion / 关联建议",
            "review_questions": "Review Questions / 复习问题",
            "action_extraction": "Action Extraction / 行动项提取",
        }

        default_model = self._editable_default_model(raw) or ""
        routing = self._editable_routing(raw)
        prompt_versions = self.cfg.prompts if hasattr(self.cfg, 'prompts') else {}

        steps: list[ProcessingWorkflowStep] = []
        from mindforge.config import REQUIRED_STAGES
        for stage in REQUIRED_STAGES:
            model_id = routing.get(stage, default_model)
            try:
                pv = prompt_versions.for_stage(stage)
            except Exception:
                pv = "v1"

            steps.append(ProcessingWorkflowStep(
                id=stage,
                label=step_labels.get(stage, stage),
                purpose=step_purposes.get(stage, ""),
                model_id=model_id,
                prompt_id=stage,
                prompt_version=pv,
                prompt_description=f"{stage} prompt — {step_purposes.get(stage, '')}",
                can_view_prompt=True,
            ))

        return ProcessingWorkflowConfig(
            active_strategy_id=active_id,
            active_strategy_label=sd.label if sd else meta.display_label if meta else active_id,
            active_strategy_description=getattr(meta, 'description', '') if meta else '',
            active_strategy_status="default workflow",
            available_strategies=available,
            workflow_steps=steps,
        )

    def _routing_is_explicit(self, raw: dict[str, Any]) -> bool:
        llm = raw.get("llm")
        return isinstance(llm, dict) and isinstance(llm.get("routing"), dict)

    def _editable_routing(self, raw: dict[str, Any]) -> dict[str, str]:
        default_model = self._editable_default_model(raw)
        if default_model is None:
            return {}
        llm = raw.get("llm")
        routing_raw = llm.get("routing") if isinstance(llm, dict) else {}
        if not isinstance(routing_raw, dict):
            routing_raw = {}
        return {
            stage: str(routing_raw.get(stage) or default_model)
            for stage in self.cfg.llm.profiles[self.cfg.llm.active_profile]
        }

    def _resolved_per_step_models(self, raw: dict[str, Any]) -> dict[str, ResolvedWorkflowModelConfig]:
        editable_models = self._editable_models(raw)
        resolved: dict[str, ResolvedWorkflowModelConfig] = {}
        for stage, model_id in self._editable_routing(raw).items():
            model = editable_models.get(model_id)
            if model is None:
                continue
            resolved[stage] = ResolvedWorkflowModelConfig(
                workflow_step=stage,
                model_id=model_id,
                type=model.type,
                base_url=model.effective_base_url,
                model=model.effective_model,
            )
        return resolved

    def _legacy_config_detected(self, raw: dict[str, Any]) -> bool:
        llm = raw.get("llm")
        return isinstance(llm, dict) and "default_model" not in llm

    def _llm_validation_errors(self, raw: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        llm = raw.get("llm")
        if not isinstance(llm, dict) or "default_model" not in llm:
            return errors
        models = llm.get("models")
        if not isinstance(models, dict):
            return ["llm.models missing"]
        # 无模型首次状态：default_model=null + models={} 合法，不报错
        if not models:
            return errors
        default_model = _str_or_none(llm.get("default_model"))
        if default_model is None or default_model not in models:
            errors.append("Please choose a default model from the configured models.")
        routing = llm.get("routing") or {}
        if isinstance(routing, dict):
            for stage, model_id in routing.items():
                if str(model_id) not in models:
                    errors.append(f"llm.routing.{stage}={model_id!r} is not defined in llm.models")
        return errors

    def _llm_warnings(self, raw: dict[str, Any]) -> list[str]:
        if self._legacy_config_detected(raw):
            return [
                "Legacy LLM config detected. Save to migrate to the new llm.models/default_model/routing format."
            ]
        return []

    def _editable_provider(self, raw: dict[str, Any], name: str) -> EditableProviderConfig:
        llm = raw.get("llm") if isinstance(raw.get("llm"), dict) else {}
        provider_raw = {}
        if isinstance(llm, dict) and isinstance(llm.get("providers"), dict):
            candidate = llm["providers"].get(name)
            provider_raw = candidate if isinstance(candidate, dict) else {}
            provider_type = str(provider_raw.get("type") or name)
            default_base_url = _str_or_none(
                provider_raw.get("default_base_url") or provider_raw.get("base_url")
            )
            default_model = _str_or_none(
                provider_raw.get("default_model") or provider_raw.get("model")
            )
            api_key_env = _str_or_none(provider_raw.get("api_key_env"))
            base_url_env = _str_or_none(provider_raw.get("base_url_env"))
            model_env = _str_or_none(provider_raw.get("model_env"))
        else:
            model = self._model_for_provider(raw, name)
            provider_type = model.type if model is not None else name
            default_base_url = model.base_url if model is not None else None
            default_model = model.model if model is not None else None
            api_key_env = model.api_key_env if model is not None else None
            base_url_env = model.base_url_env if model is not None else None
            model_env = model.model_env if model is not None else None

        api_key_present = self._process_env_present(api_key_env)
        effective_base_url, base_url_source = self._effective_non_secret_value(
            env_name=base_url_env,
            default_value=default_base_url,
        )
        effective_model, model_source = self._effective_non_secret_value(
            env_name=model_env,
            default_value=default_model,
        )
        return EditableProviderConfig(
            name=name,
            type=provider_type,
            default_base_url=default_base_url,
            default_model=default_model,
            api_key_env=api_key_env,
            api_key_status="present" if api_key_present else "missing",
            api_key_env_configured=bool(api_key_env),
            api_key_secret_present=api_key_present,
            api_key_masked_value=_masked_secret(os.environ.get(api_key_env, ""))
            if api_key_present and api_key_env
            else None,
            api_key_status_label=_api_key_status_label(api_key_env, api_key_present),
            base_url_env=base_url_env,
            base_url_env_present=self._env_present(base_url_env),
            base_url_env_status=self._process_env_status(base_url_env),
            effective_base_url=effective_base_url,
            base_url_source=base_url_source,
            model_env=model_env,
            model_env_present=self._env_present(model_env),
            model_env_status=self._process_env_status(model_env),
            effective_model=effective_model,
            model_source=model_source,
        )

    def _env_present(self, env_name: str | None) -> bool:
        if not env_name:
            return False
        dotenv = self._read_dotenv_presence()
        return env_name in os.environ or env_name in dotenv.keys

    def _process_env_present(self, env_name: str | None) -> bool:
        return bool(env_name and env_name in os.environ and os.environ[env_name])

    def _process_env_status(self, env_name: str | None) -> str:
        if not env_name:
            return "not_configured"
        return "present" if self._process_env_present(env_name) else "missing"

    def _effective_non_secret_value(
        self,
        *,
        env_name: str | None,
        default_value: str | None,
    ) -> tuple[str | None, str]:
        if self._process_env_present(env_name):
            assert env_name is not None
            return os.environ[env_name], "env"
        if default_value:
            return default_value, "config_default"
        return None, "missing"

    def _model_for_provider(self, raw: dict[str, Any], provider: str):
        llm = raw.get("llm")
        if not isinstance(llm, dict):
            return None
        profiles = llm.get("profiles")
        if not isinstance(profiles, dict):
            return None
        profile = profiles.get(provider)
        if not isinstance(profile, dict):
            return None
        for alias in profile.values():
            model = self.cfg.llm.models.get(str(alias))
            if model is not None and model.type != "fake":
                return model
        for alias in profile.values():
            model = self.cfg.llm.models.get(str(alias))
            if model is not None:
                return model
        return None

    def _apply_provider_patch(
        self,
        raw: dict[str, Any],
        provider: str,
        provider_patch,
    ) -> None:
        llm = raw.setdefault("llm", {})
        if not isinstance(llm, dict):
            raise ConfigUpdateError(["llm must be a YAML object"])
        providers = llm.get("providers")
        if isinstance(providers, dict):
            item = providers.setdefault(provider, {})
            if not isinstance(item, dict):
                raise ConfigUpdateError([f"llm.providers.{provider} must be a YAML object"])
            _assign_if_present(item, "default_base_url", provider_patch.default_base_url)
            _assign_if_present(item, "default_model", provider_patch.default_model)
            # env var name 字段不写回 YAML（与 model 保存保持一致）
            for env_key in ("api_key_env", "base_url_env", "model_env", "version_env"):
                item.pop(env_key, None)
            return

        profiles = llm.get("profiles")
        models = llm.get("models")
        if not isinstance(profiles, dict) or not isinstance(models, dict):
            raise ConfigUpdateError(["legacy llm.profiles/models are required"])
        profile = profiles.get(provider)
        if not isinstance(profile, dict):
            raise ConfigUpdateError([f"llm.profiles.{provider} is not configured"])
        aliases = sorted({str(alias) for stage, alias in profile.items() if stage in self.cfg.llm.profiles[provider]})
        for alias in aliases:
            model = models.get(alias)
            if not isinstance(model, dict):
                continue
            _assign_if_present(model, "base_url", provider_patch.default_base_url)
            _assign_if_present(model, "model", provider_patch.default_model)
            for env_key in ("api_key_env", "base_url_env", "model_env", "version_env"):
                model.pop(env_key, None)

    def _apply_llm_model_routing_patch(self, raw: dict[str, Any], patch: SetupConfigPatch) -> None:
        """保存 Setup 新 LLM 语义，不把 legacy profile/provider 写回用户配置。

        Secret 处理：api_key_action 决定 secret store 行为——
        - "update" + api_key → 写入 secret store
        - "clear" → 删除 secret store 中的 key
        - "keep" 或缺失 → 保留已有 secret（不读也不写）

        普通保存不写出 env var name 字段（api_key_env/base_url_env/model_env）。
        这些字段仅用于 Advanced env mode（读兼容），不写回用户 YAML。
        """

        llm = raw.setdefault("llm", {})
        if not isinstance(llm, dict):
            raise ConfigUpdateError(["llm must be a YAML object"])
        if patch.default_model:
            llm["default_model"] = patch.default_model
        if patch.models:
            # 检测被删除的 model_id，清理对应的 secret store 条目
            existing_ids = set(self._all_model_ids(raw))
            new_ids = set(patch.models.keys())
            for deleted_id in existing_ids - new_ids:
                self.secrets.remove(deleted_id)
            llm["models"] = {}
        models = llm.setdefault("models", {})
        if not isinstance(models, dict):
            raise ConfigUpdateError(["llm.models must be a YAML object"])
        for model_id, model_patch in patch.models.items():
            item = models.setdefault(model_id, {})
            if not isinstance(item, dict):
                raise ConfigUpdateError([f"llm.models.{model_id} must be a YAML object"])
            # 产品字段：type, base_url, model —— 这些是普通用户配置的
            _assign_if_present(item, "type", model_patch.type)
            _assign_if_present(item, "base_url", model_patch.base_url)
            _assign_if_present(item, "model", model_patch.model)
            if model_patch.api_key_optional is not None:
                item["api_key_optional"] = model_patch.api_key_optional
            # env var name 字段不写回 YAML；仅 Advanced env mode 显式开关时保留
            # （本轮不做开关：只读兼容，不写回）
            for env_key in ("api_key_env", "base_url_env", "model_env", "version_env"):
                item.pop(env_key, None)
            # 处理 API key：写入/清除/保留 secret store
            self._apply_api_key_patch(model_id, model_patch)
        routing_raw = llm.get("routing")
        existing_routing = routing_raw if isinstance(routing_raw, dict) else {}
        explicit_routing = dict(existing_routing)
        if patch.routing:
            explicit_routing.update(patch.routing)
        default_model = _str_or_none(llm.get("default_model"))
        if default_model:
            # 中文学习型说明：Setup 保存时把五段 routing 写完整，便于用户审计
            # YAML；runtime 仍会 fallback 到 default_model，以兼容旧 dogfood 配置。
            llm["routing"] = {
                stage: str(explicit_routing.get(stage) or default_model)
                for stage in REQUIRED_STAGES
            }
        elif patch.routing:
            llm["routing"] = dict(patch.routing)
        elif "routing" in llm:
            llm.pop("routing", None)
        for legacy_key in ("active", "active_profile", "providers", "profiles"):
            llm.pop(legacy_key, None)

    @staticmethod
    def _all_model_ids(raw: dict[str, Any]) -> set[str]:
        llm = raw.get("llm")
        if not isinstance(llm, dict):
            return set()
        models = llm.get("models")
        if not isinstance(models, dict):
            return set()
        return {str(k) for k, v in models.items() if isinstance(v, dict)}

    def _apply_api_key_patch(self, model_id: str, model_patch) -> None:
        """根据 api_key_action 处理 secret store 写入。"""
        action = model_patch.api_key_action or "keep"
        if action == "clear":
            self.secrets.remove(model_id)
        elif action == "update" and model_patch.api_key:
            self.secrets.set(model_id, model_patch.api_key)
        # "keep" — 不触碰 secret store

    def _api_key_source(
        self,
        model_id: str,
        model_type: str,
        api_key_env: str | None,
    ) -> str:
        """判断 API key 来源：local_secret > env > demo > missing。"""
        # demo/fake 模型不需要真实 API key
        if model_type == "fake":
            return "demo"
        # secret store 是最直接的用户输入
        if self.secrets.present(model_id):
            return "local_secret"
        # env var 是部署模式
        if api_key_env and api_key_env in os.environ and os.environ[api_key_env]:
            return "env"
        return "missing"

    def _masked_api_key_value(
        self,
        model_id: str,
        api_key_env: str | None,
        api_key_source: str,
    ) -> str | None:
        """生成脱敏 key 供前端展示，不返回 raw value。"""
        if api_key_source == "local_secret":
            return self.secrets.masked(model_id)
        if api_key_source == "env" and api_key_env:
            raw = os.environ.get(api_key_env, "")
            return _masked_secret(raw) if raw else None
        return None

    def _deleted_model_ids(
        self,
        raw: dict[str, Any],
        patch: SetupConfigPatch,
    ) -> set[str]:
        """返回 patch 中省略的（被删除的）model_id。"""
        existing = self._all_model_ids(raw)
        if patch.models is None:
            return set()
        new = set(patch.models.keys())
        return existing - new

    def _create_vault_dirs(self, root: Path) -> None:
        try:
            root.mkdir(parents=True, exist_ok=True)
            (root / self.cfg.vault.inbox_root).mkdir(parents=True, exist_ok=True)
            (root / self.cfg.vault.cards_dir).mkdir(parents=True, exist_ok=True)
            (root / self.cfg.vault.projects_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConfigUpdateError([f"Cannot create vault directory: {root}"]) from exc

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


class ConfigUpdateError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _assign_if_present(target: dict[str, Any], key: str, value: str | None) -> None:
    if value is not None:
        target[key] = value


def _masked_secret(value: str) -> str:
    suffix = value[-4:] if len(value) >= 4 else value
    prefix = "sk-" if value.startswith("sk-") else ""
    return f"{prefix}****{suffix}"


def _api_key_status_label(env_name: str | None, present: bool) -> str:
    if present:
        raw = os.environ.get(env_name or "", "")
        return f"present ({_masked_secret(raw)})"
    if env_name:
        return "env name configured, value missing"
    return "env name missing"


def _is_product_provider(name: str, provider_type: Any) -> bool:
    text = f"{name} {provider_type or ''}".lower()
    blocked = ("fake", "local", "test", "default")
    return not any(token in text for token in blocked)


def _is_product_model(model: Any) -> bool:
    """模型是否应作为产品模型出现在主 UI（非 fake/test/demo/default 内部模型）。

    fake/mock/demo 模型仍可被测试直接构造，但不能作为普通用户 Web Setup
    下拉和卡片暴露出来。
    """
    if not isinstance(model, dict):
        return False
    model_type = str(model.get("type") or "")
    provider = str(model.get("provider") or "")
    text = f"{provider} {model_type}".lower()
    blocked = ("fake", "test", "default", "demo")
    return not any(token in text for token in blocked)


def _is_product_model_entry(model_id: str, model_type: Any) -> bool:
    text = f"{model_id} {model_type or ''}".lower()
    blocked = ("fake", "test", "default", "demo")
    return not any(token in text for token in blocked)


def _is_dangerous_vault_path(path: Path) -> bool:
    dangerous = [
        Path("/System"),
        Path("/bin"),
        Path("/sbin"),
        Path("/usr/bin"),
        Path("/usr/sbin"),
        Path("/etc"),
        Path("/private/etc"),
    ]
    if path == Path("/"):
        return True
    for root in dangerous:
        try:
            if path == root or path.is_relative_to(root):
                return True
        except ValueError:
            continue
    return False


def _cubox_paths(raw: dict[str, Any]) -> tuple[str | None, str | None]:
    cubox = raw.get("cubox")
    if not isinstance(cubox, dict):
        return None, None
    return _str_or_none(cubox.get("export_path")), _str_or_none(cubox.get("import_path"))
