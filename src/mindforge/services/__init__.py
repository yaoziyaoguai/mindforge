"""MindForge service 层包入口。

中文学习型说明：
- ``services/`` 目录承载"用例编排"的纯逻辑：接收 ``MindForgeConfig`` 与
  最小事实输入，返回结构化数据；不进行 Rich/Console/Typer 渲染，也不直接
  与 CLI 入口耦合。
- 这样 CLI 层退化为 thin adapter，service 可以独立单测，未来若引入新的
  入口（API / TUI / job runner）也无需复制 doctor 等业务逻辑。
"""
