"""Custom strategy *review-only* preview packet（v0.12 Slice 5 Green）。

为什么要单独一个 preview_packet 模块？
=====================================

到 Slice 4 为止：``custom.py`` 把 YAML 校验成数据；``custom_loader.py``
把磁盘加载成数据；``__init__.py.build_strategy`` 拒绝执行 custom。
但用户写完 custom YAML 后，仍缺一个**只读、稳定、可被 CLI / 未来 UI /
文档生成器统一消费**的输出形态——告诉用户：

- 这个策略是谁；
- 校验过没有；
- 为什么暂时不能执行；
- 它既不是 AI 草稿，也不是人工已批准的卡，更不会进入 writer
  / approval。

这正是 *preview packet* 的唯一职责：把已校验或已被拒绝的
``StrategyDefinition`` / ``InvalidStrategyDefinitionError`` 翻译成一份
**review-only** 数据 + 一份**纯文本**渲染。它既不是策略元数据
（``StrategyMetadata`` 那一份是给 registry 看的），也不是知识卡
（``KnowledgeCard`` 是真正会被 approve 的工件）。它是介于"我看见了
这个 custom 配置"和"未来某天才可能执行它"之间的**安全 review 桥**。

本模块的硬边界（高内聚 + 信息隐藏）
====================================

- **只**消费 ``StrategyDefinition`` 与 ``InvalidStrategyDefinitionError``；
- **只**返回 ``dict``（packet）与 ``str``（rendered text）；
- **不**构造任何 LLM 客户端 / provider；
- **不**触碰 dotenv / 真实文件系统（除被动接收路径字符串外）；
- **不**调用 card-writer / approval-service / approve 路径；
- **不**注册到 ``StrategyRegistry``；
- **不**把 ``status`` 升级成 ``implemented``；
- packet 字段表里**永远不含**任何 approved-flag 字面量；
- 渲染输出**不**暴露 raw Python ``repr`` / Traceback / 内存地址。

如果以后要做 UI、TUI、JSON 输出、capability matrix，都应该消费本模块
的 packet/render，而不是再去戳 ``StrategyDefinition`` 内部。这就是
本模块的**信息隐藏**职责。

源码 source-scan 契约
=====================

配套契约测试通过 AST + 字面量扫描固化"本模块禁止任何 arbitrary code
execution / shell / network / secrets / vault-write / approval-flag
触点"——具体禁用 token 清单由测试维护，本注释刻意不再列字面量以免
触发自身 source-scan。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .custom import InvalidStrategyDefinitionError, StrategyDefinition

__all__ = [
    "build_custom_preview_packet",
    "build_invalid_preview_packet",
    "render_custom_preview_packet",
]


# 中文学习型注释：preview packet 的"形状"是 v0.12 的对外契约。
# 一旦 CLI / 未来 UI 开始消费 packet["kind"] / packet["executable"]，
# 改字段就是 breaking change。所以字段集合刻意收敛、显式列出，便于审计。
_PREVIEW_KIND: str = "preview_only"


def build_custom_preview_packet(
    definition: StrategyDefinition,
) -> dict[str, Any]:
    """把已校验的 :class:`StrategyDefinition` 翻译成 review-only packet。

    输出是 plain ``dict``，因此可直接 ``json.dumps`` / 渲染 / 入测试断言。
    输入是 frozen dataclass，本函数不 mutate；输出与输入字段名对齐，
    额外加 3 个边界声明字段：

    - ``validation_status="valid"``：本入口仅接受已通过 parse 的 definition；
    - ``executable=False``：明示这是 preview，不可被任何 runtime 触发；
    - ``kind="preview_only"``：稳定 discriminator，区别于 ai_draft / card。

    刻意**不**输出任何"已批准"标志字段——下游 serializer 都不
    应能从 packet 反推出"这是已批准卡"的错觉。
    """

    return {
        "strategy_id": definition.strategy_id,
        "strategy_version": definition.strategy_version,
        "display_name": definition.display_name,
        "description": definition.description,
        "provider_mode": definition.provider_mode,
        "safety_policy": definition.safety_policy,
        "output_schema_id": definition.output_schema_id,
        "status": definition.status,
        "validation_status": "valid",
        "executable": False,
        "kind": _PREVIEW_KIND,
    }


def build_invalid_preview_packet(
    source_path: Path | str,
    error: InvalidStrategyDefinitionError,
) -> dict[str, Any]:
    """对**校验失败**的 custom YAML 也产出一份 packet。

    这里的设计取舍：与其让 CLI 自己捕获异常 + 拼字符串，不如统一让
    presenter 消费同一形状的 packet。这样：

    - CLI / 未来 UI 只需识别 ``validation_status != "valid"`` 即可走错误展示；
    - 错误信息以**安全字符串**形式落入 packet（不抛栈、不带 repr）；
    - ``kind`` 仍然是 ``preview_only`` —— invalid 也是 review，不是执行。

    刻意**不**附原始 ``error.__traceback__``，避免任何渲染层把内部栈
    回显给用户（栈里可能含本地路径 / 行号 / 内部模块名，对终端用户无用、
    对安全无益）。
    """

    return {
        "source_path": str(source_path),
        "validation_status": "invalid",
        "validation_error": str(error),
        "executable": False,
        "kind": _PREVIEW_KIND,
    }


def render_custom_preview_packet(packet: Mapping[str, Any]) -> str:
    """把 packet 渲染成 *user-readable* 纯文本。

    设计目标：
    - 终端可直接 print，无需 Rich / 颜色依赖（保持 presenter 低耦合）；
    - 必含 ``preview`` + ``not executable`` + ``ai_draft_only`` 关键字，
      确保下游脚本 / 测试可对子串断言；
    - 校验失败 packet 渲染必含 ``source_path`` 与 "validation"；
    - **不**输出 raw repr、内存地址、Traceback、``<class …>`` 等字面量。

    单一函数处理 valid 与 invalid 两种 packet——分支用 ``validation_status``
    判别，避免再多导出一个 render_invalid 把 API 表面拆碎。
    """

    if packet.get("validation_status") == "valid":
        return _render_valid(packet)
    return _render_invalid(packet)


def _render_valid(packet: Mapping[str, Any]) -> str:
    lines = [
        f"Custom strategy preview: {packet['strategy_id']}"
        f" (v{packet['strategy_version']})",
        f"  display_name      : {packet['display_name']}",
        f"  description       : {packet['description']}",
        f"  provider_mode     : {packet['provider_mode']}",
        f"  safety_policy     : {packet['safety_policy']} (ai_draft_only)",
        f"  output_schema_id  : {packet['output_schema_id']}",
        f"  status            : {packet['status']}",
        f"  validation_status : {packet['validation_status']}",
        "  executable        : false (preview only — not executable)",
        "  note              : preview is review-only; not ai_draft yet,",
        "                      not approved, not written to vault.",
    ]
    return "\n".join(lines)


def _render_invalid(packet: Mapping[str, Any]) -> str:
    lines = [
        f"Custom strategy preview (invalid): {packet['source_path']}",
        f"  validation_status : {packet['validation_status']}",
        f"  validation_error  : {packet['validation_error']}",
        "  executable        : false (preview only — not executable)",
        "  hint              : fix the YAML and re-run discovery.",
    ]
    return "\n".join(lines)
