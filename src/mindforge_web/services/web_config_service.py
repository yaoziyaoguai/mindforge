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

from mindforge.config import MindForgeConfig
from mindforge.cubox_readiness import classify_cubox_real_opt_in, inspect_cubox_config
from mindforge.provider_readiness import build_readiness_report

from mindforge_web.schemas import (
    EditableCuboxConfig,
    EditableLLMConfig,
    EditableProviderConfig,
    EditableVaultConfig,
    EnvKeyStatus,
    NextAction,
    ProviderAliasStatus,
    ProviderStatus,
    SetupConfigPatch,
    SetupEditableConfigResponse,
    SetupValidationResponse,
    StatusItem,
)


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
                available_providers=self._available_provider_names(raw),
                providers=self._editable_providers(raw),
                readiness=self.provider_status(),
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
                value="managed on Sources page",
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
                elif not resolved.exists() and not patch.create_vault:
                    errors.append(
                        "Vault path does not exist. Create it first or enable create_vault."
                    )
                elif resolved.exists() and not resolved.is_dir():
                    errors.append("Vault path must be a directory.")

        if patch.active_provider is not None and patch.active_provider not in self._available_provider_names(raw):
            errors.append(
                f"Active provider {patch.active_provider!r} is not configured."
            )

        for provider, provider_patch in patch.providers.items():
            if provider not in self._available_provider_names(raw):
                errors.append(f"Provider {provider!r} is not configured.")
            for field_name in ("api_key_env", "base_url_env", "model_env"):
                value = getattr(provider_patch, field_name)
                if value is not None and value.strip() and not value.strip().isidentifier():
                    errors.append(f"{provider}.{field_name} must be an env var name.")

        if patch.cubox_export_path:
            warnings.append("Cubox JSON path is stored as non-secret local setup metadata.")

        return SetupValidationResponse(ok=not errors, errors=errors, warnings=warnings)

    def update_patch(self, patch: SetupConfigPatch) -> None:
        validation = self.validate_patch(patch)
        if not validation.ok:
            raise ConfigUpdateError(validation.errors)

        raw = self._read_config_raw()
        if patch.vault_root is not None:
            resolved = Path(patch.vault_root).expanduser().resolve(strict=False)
            if patch.create_vault:
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

        if patch.cubox_export_path is not None or patch.cubox_import_path is not None:
            cubox = raw.setdefault("cubox", {})
            if not isinstance(cubox, dict):
                raise ConfigUpdateError(["cubox must be a YAML object"])
            if patch.cubox_export_path is not None:
                cubox["export_path"] = patch.cubox_export_path
            if patch.cubox_import_path is not None:
                cubox["import_path"] = patch.cubox_import_path

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

    def _editable_providers(self, raw: dict[str, Any]) -> dict[str, EditableProviderConfig]:
        providers: dict[str, EditableProviderConfig] = {}
        for name in self._available_provider_names(raw):
            providers[name] = self._editable_provider(raw, name)
        return providers

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
            _assign_if_present(item, "api_key_env", provider_patch.api_key_env)
            _assign_if_present(item, "base_url_env", provider_patch.base_url_env)
            _assign_if_present(item, "model_env", provider_patch.model_env)
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
            _assign_if_present(model, "api_key_env", provider_patch.api_key_env)
            _assign_if_present(model, "base_url_env", provider_patch.base_url_env)
            _assign_if_present(model, "model_env", provider_patch.model_env)

    def _create_vault_dirs(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / self.cfg.vault.inbox_root).mkdir(parents=True, exist_ok=True)
        (root / self.cfg.vault.cards_dir).mkdir(parents=True, exist_ok=True)
        (root / self.cfg.vault.projects_dir).mkdir(parents=True, exist_ok=True)

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
