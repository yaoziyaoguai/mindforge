"""SourceAdapter 抽象与各 adapter 实现。

本子包是 MindForge **多源接入的协议层**。所有业务模块（Triager / Distiller /
Linker / Writer）只依赖 ``base.SourceDocument``，**不**直接接触 Cubox / PDF /
Docx 等具体格式。新增源类型 = 新增一个 adapter，不改核心加工逻辑。
"""
