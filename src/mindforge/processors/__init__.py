"""processors — 五个 stage 的业务实现。

每个 processor 是一个**纯函数**：

    run_<stage>(*, client, logger, source, ctx, ...) -> dict

- 输入：``LLMClient`` / ``RunLogger`` / SourceDocument / 上下文变量。
- 行为：
  1. 加载 + 渲染对应 prompt；
  2. 调用 ``client.generate(stage=...)``；
  3. 解析 JSON 输出（失败抛 :class:`StageError`）；
  4. 通过 ``logger.emit("llm_call", ...)`` 记一行可回放事件
     （**只**记 stage / model_alias / provider / actual_model /
     prompt_version / input_file_hash / status / tokens / latency；
     **不**记 prompt 全文 / response 全文 / raw_text）；
  5. 返回解析后的 ``dict``。

这一层故意保持薄：**一切跨 stage 的编排逻辑放在 ``pipeline``**。
"""

from .base import StageError, StageResult, run_stage
from .pipeline import Pipeline, PipelineOutcome

__all__ = [
    "StageError",
    "StageResult",
    "run_stage",
    "Pipeline",
    "PipelineOutcome",
]
