# 我自己关于 my-first-agent 项目的临时想法

> 虚构示例 ManualNote。

随手记：
- 工具调用前要打日志，错误必须可回放；
- agent 不应该自己决定 prompt，prompt 应该来自 harness；
- 重要状态都要 checkpoint。

待办：
- 把 tool registry 抽出来；
- 给每个 tool 加超时；
- 为 long-running tool 加 cancel。
