"""MindForge — 多源接入 AI 知识加工管线（v0.1）。

本包目前仅作为命名空间存在；具体业务模块在 M1 起逐步加入：
- ``mindforge.sources``  — SourceAdapter 抽象与各 adapter 实现（M1）
- ``mindforge.models``   — 通用数据模型（M1）
- ``mindforge.config``   — 加载并校验 configs/mindforge.yaml（M1）
- ``mindforge.checkpoint`` — state.json 读写（M1）
- ``mindforge.scanner``  — 扫描 inbox 派发到 adapter（M1）
- ``mindforge.llm``      — LLMClient + Provider 抽象（M2）
- ``mindforge.{triager,distiller,linker,writer}`` — 加工与落盘（M2/M3）
- ``mindforge.cli``      — 命令行入口（M1 起逐步加入 scan/status/process）

所有契约的权威源是 ``docs/MINDFORGE_PROTOCOL.md``。
"""

__version__ = "0.7.10"
