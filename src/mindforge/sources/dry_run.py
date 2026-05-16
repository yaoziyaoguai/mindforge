"""v0.2 source-layer dry-run integration seam。

让 v0.2 ``AdapterRegistry`` + ``SourceAdapter`` 可被验证和预览，
但不改变 v0.1 默认 import/watch/process 行为。

两个入口
--------

``classify_source_path(path, registry=None)``
    纯查询：判断某个路径能否被当前 registry 中的某个 adapter 处理。
    返回 dict，包含 matched / adapter_name / source_type / status。
    不调用 adapter.load、不读文件内容、不处理 secrets。

``preview_source_load(path, registry=None)``
    显式 opt-in：用 registry 找到 adapter 并调用 load(path)。
    返回 AdapterResult（loaded / skipped / failed）。
    仅供 tests / future CLI opt-in seam 使用，不接入默认主链路。

默认 registry
-------------
如果 ``registry is None``，使用 ``create_default_registry()``。
M1 阶段仅注册 PlainMarkdownAdapter。
"""

from __future__ import annotations

from mindforge.sources.adapter_result import AdapterResult, SkipReason
from mindforge.sources.registry import AdapterRegistry, create_default_registry


def classify_source_path(path: str, registry: AdapterRegistry | None = None) -> dict:
    """判断路径能否被 registry 中的某个 adapter 处理。

    纯查询：仅通过 ``registry.find_for_path`` → ``adapter.can_handle`` 判断，
    不调用 ``adapter.load``、不读文件、不处理 secrets。

    返回 dict：
    - ``matched``：是否找到匹配的 adapter
    - ``status``：``"matched"`` 或 ``"unsupported"``
    - ``adapter_name``：匹配的 adapter.name（或 None）
    - ``source_type``：匹配的 adapter.source_type（或 None）
    - ``path``：传入的原始路径
    """
    reg = registry if registry is not None else create_default_registry()
    adapter = reg.find_for_path(path)

    if adapter is not None:
        return {
            "matched": True,
            "status": "matched",
            "adapter_name": adapter.name,
            "source_type": adapter.source_type,
            "path": path,
        }

    return {
        "matched": False,
        "status": "unsupported",
        "adapter_name": None,
        "source_type": None,
        "path": path,
    }


def preview_source_load(path: str, registry: AdapterRegistry | None = None) -> AdapterResult:
    """显式 opt-in：用 registry 找到 adapter 并调用 load(path)。

    返回 AdapterResult（loaded / skipped / failed）。
    仅供 tests / future CLI opt-in seam 使用，不接入默认主链路。

    三态路径：
    - 有匹配 adapter + 文件合法 → ``AdapterResult.loaded``
    - 无匹配 adapter → ``AdapterResult.skipped``（unsupported format）
    - 有匹配 adapter + load 失败 → ``AdapterResult.failed``（由 adapter.load 返回）
    """
    reg = registry if registry is not None else create_default_registry()
    adapter = reg.find_for_path(path)

    if adapter is None:
        return AdapterResult(
            status="skipped",
            skip_reason=SkipReason.UNSUPPORTED_FORMAT,
        )

    return adapter.load(path)


__all__ = [
    "classify_source_path",
    "preview_source_load",
]
