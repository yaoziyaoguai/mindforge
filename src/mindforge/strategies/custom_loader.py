"""Custom strategy loading source（v0.12 Slice 2 Green）。

为什么独立成 ``custom_loader.py`` 而不是塞进 ``custom.py``？
============================================================

``custom.py`` 已经把 *声明 + 校验* 的契约钉得很死（v0.12 Slice 1）。
Slice 2 引入"从文件 / 目录读取"是另一条**正交**职责：

- ``custom.py`` 关心"这个 dict 合不合法"；
- ``custom_loader.py`` 关心"这个文件能不能安全打开 + 解析为 dict"。

把它们合成一个文件会让"读文件"与"校验数据"耦合在一起，未来想加更多
loading source（HTTP fetch、远端 manifest）会立刻把 custom.py 撑成
小巨石，所以这里**故意**拆开，但只拆出这一个高内聚模块，不再继续
机械拆。

本模块的职责（高内聚）
========================

- 暴露 :func:`load_strategy_definition_from_file` —— 从单个 YAML/JSON
  文件读 + 解析 + 委派给 ``parse_strategy_definition``；
- 暴露 :func:`load_strategy_definitions_from_directory` —— 从一个**显式
  指定**目录读取所有 declarative 扩展名文件；
- 暴露 :class:`StrategyDefinitionFileError`（继承
  :class:`InvalidStrategyDefinitionError`）作为 file 级错误的统一出口。

本模块明确**不**承担
====================

- 不隐式扫描用户主目录、Obsidian vault、私人 workspace、``.env``；
- 不跟随 symlink 越界目录；
- 不接受 ``..`` 路径穿越；
- 不接受 ``.py`` / ``.sh`` 等可疑可执行扩展名（即便其内容恰好可被 YAML
  解析）；
- 不调用任何 provider / LLM / network；
- 不把 custom 定义注册进 ``StrategyRegistry`` —— registry 接入是后续
  slice 的事；
- 不持有 prompt / runtime / Typer command / RunLogger。

源码安全 source-scan 契约
==========================

本文件**不允许**任何 arbitrary code execution / shell / network /
secrets / Cubox / Upstage / dotenv 触点；也不允许任何 implicit
home-directory / vault / config 隐式扫描 token（具体 token 清单由
``test_loader_source_has_no_arbitrary_execution_or_network_tokens`` /
``test_loader_source_has_no_implicit_scanning_tokens`` 维护，本注释
刻意不列出字面量以免触发自身 source-scan）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .custom import (
    InvalidStrategyDefinitionError,
    StrategyDefinition,
    parse_strategy_definition,
)


class StrategyDefinitionFileError(InvalidStrategyDefinitionError):
    """从文件读取 / 解析 custom strategy definition 失败。

    继承 :class:`InvalidStrategyDefinitionError`，让上层既有"任何 custom
    定义出问题"的 broad except 仍能 catch；同时类身份独立，便于把
    "*文件* 级错误"（路径 / 扩展名 / 语法）与"*数据* 级错误"（字段
    校验）在 UX 层分流。
    """


# 中文学习型注释：白名单扩展名 = 只接受 *声明式* 序列化格式。
# 任何 ``.py`` / ``.sh`` / ``.bin`` / 无扩展文件都会在 loader 入口被
# 拒绝，**不**进入 yaml.safe_load —— 即便 YAML 偏好宽松解析，这条
# 防线也保证 loader 不会被诱导触碰可疑可执行文件。
_DECLARATIVE_EXTENSIONS: frozenset[str] = frozenset({".yaml", ".yml", ".json"})


def _file_error(path: Path, reason: str) -> StrategyDefinitionFileError:
    """构造带文件路径的友好错误（不暴露 raw Python repr / Traceback）。"""

    return StrategyDefinitionFileError(f"{path}: {reason}")


def _ensure_declarative_extension(path: Path) -> None:
    """拒绝非 declarative 扩展名（含无扩展）。"""

    if path.suffix.lower() not in _DECLARATIVE_EXTENSIONS:
        raise _file_error(
            path,
            f"unsupported file extension {path.suffix!r}; "
            f"only {sorted(_DECLARATIVE_EXTENSIONS)} are accepted "
            "for declarative custom strategy definitions.",
        )


def _ensure_no_path_traversal(path: Path) -> None:
    """拒绝包含 ``..`` 段的输入路径。

    用户必须显式给出落到目标目录里的路径，不能用 ``..`` 跳出。即便
    最终 resolve 到的文件存在且合法，也拒绝 —— 显式 > 神秘。
    """

    if ".." in path.parts:
        raise _file_error(
            path,
            "path contains '..' segments; loader requires explicit paths "
            "without parent-directory traversal.",
        )


def _read_text_safely(path: Path) -> str:
    """读取文件文本；不存在 / 不是普通文件 → 友好错误。"""

    if not path.exists():
        raise _file_error(path, "file does not exist")
    if not path.is_file():
        raise _file_error(path, "path is not a regular file")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        # 中文学习型注释：把 OSError 收口为 file 级错误 —— 不让
        # raw OSError 直接冒到用户终端。
        raise _file_error(path, f"failed to read file: {exc.strerror}") from exc


def _parse_text_to_data(path: Path, text: str) -> Any:
    """按扩展名选择 JSON / YAML 解析；任何解析错误统一收口。"""

    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            return json.loads(text)
        # YAML safe_load 涵盖 .yaml / .yml；safe_load **不**支持
        # ``!python/object`` 之类危险标签 —— 保持 declarative。
        return yaml.safe_load(text)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise _file_error(
            path,
            f"failed to parse declarative content: {exc.__class__.__name__}",
        ) from exc


def load_strategy_definition_from_file(path: Path) -> StrategyDefinition:
    """从一个**显式**文件路径加载并解析 custom strategy definition。

    安全门顺序（每一步都即时拒绝，错误消息含文件路径，便于用户定位）：

    1. 路径中不允许含 ``..``（防 path traversal）；
    2. 扩展名必须 ∈ ``{.yaml, .yml, .json}``；
    3. 文件必须存在且是普通文件；
    4. 内容必须是合法 JSON / YAML；
    5. 解析得到的 dict 必须通过 ``parse_strategy_definition`` 校验。

    任何分支都不读 ``.env`` / 不调 provider / 不写 workspace / 不执行
    用户提供的内容。
    """

    _ensure_no_path_traversal(path)
    _ensure_declarative_extension(path)
    text = _read_text_safely(path)
    data = _parse_text_to_data(path, text)
    if not isinstance(data, dict):
        raise _file_error(
            path,
            f"top-level declarative content must be a mapping; "
            f"got {type(data).__name__}.",
        )
    try:
        return parse_strategy_definition(data)
    except InvalidStrategyDefinitionError as exc:
        # 中文学习型注释：把 *数据* 级错误升级为 *文件* 级错误，附上
        # 出错文件路径 —— 用户在 CLI 看到 "{path}: ..." 而不是裸字段
        # 错误，定位更快；同时保留原异常作为 cause 便于调试链。
        raise _file_error(path, str(exc)) from exc


def iter_strategy_definition_files(directory: Path) -> tuple[Path, ...]:
    """返回 ``directory`` 下符合 declarative 规则的候选文件路径。

    与 :func:`load_strategy_definitions_from_directory` 共享同一套筛选与
    安全策略 —— 抽出独立函数是为了让 CLI / 未来 UI 在做"逐文件友好错误
    展示"时不必自己重复白名单与 symlink-escape 检查（避免规则双源不
    一致）。

    规则：

    - **不**递归子目录；
    - 只保留白名单扩展名（``.yaml`` / ``.yml`` / ``.json``）；
    - symlink 必须仍位于 ``directory`` 内，否则抛
      :class:`StrategyDefinitionFileError`；
    - 输出按文件名字典序稳定排序。

    任何分支都不读 ``.env`` / 不调 provider / 不写 workspace。
    """

    if not directory.exists() or not directory.is_dir():
        raise _file_error(directory, "directory does not exist")

    base_resolved = directory.resolve()
    candidates: list[Path] = []
    for entry in sorted(directory.iterdir()):
        if entry.suffix.lower() not in _DECLARATIVE_EXTENSIONS:
            continue
        if entry.is_symlink():
            real = entry.resolve()
            try:
                real.relative_to(base_resolved)
            except ValueError as exc:
                raise _file_error(
                    entry,
                    "symlink escapes the explicit loading directory; "
                    "loader refuses to follow links pointing outside "
                    "the requested base.",
                ) from exc
        candidates.append(entry)
    return tuple(candidates)


def load_strategy_definitions_from_directory(
    directory: Path,
) -> tuple[StrategyDefinition, ...]:
    """从一个**显式**目录加载所有 declarative custom strategy definitions。

    设计取舍：

    - **不**递归子目录（避免意外吞下用户放在子目录的非 strategy 文件）；
    - 只接受白名单扩展名的文件；其它文件**忽略**（``README.md`` 等可
      与策略文件共存而不报错）；
    - 任何**符合扩展名**的文件若校验失败，立即抛 file 级错误（不静默
      跳过）—— 静默会让用户的安全字段被默默丢弃；
    - 拒绝跟随指向目录之外的 symlink（防 symlink-escape 攻击）；
    - 输出按文件名字典序稳定排序，方便 UX 一致性。

    任何分支都不读 ``.env`` / 不调 provider / 不写 workspace / 不递归
    扫描用户其它目录。
    """

    return tuple(
        load_strategy_definition_from_file(p)
        for p in iter_strategy_definition_files(directory)
    )


__all__ = [
    "StrategyDefinitionFileError",
    "iter_strategy_definition_files",
    "load_strategy_definition_from_file",
    "load_strategy_definitions_from_directory",
]
