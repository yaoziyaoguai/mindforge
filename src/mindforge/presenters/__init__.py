"""MindForge presenter 层包入口。

中文学习型说明：
- ``presenters/`` 只负责"用户能看到什么"：把 service 层返回的结构化数据
  渲染成 Rich markup / 人类可读字符串。
- presenter 不能含业务判断（不能在这里决定"该不该 init / 该不该 demo"），
  它只翻译。这样 CLI 命令体保持瘦，未来切换渲染（普通 stdout、JSON、HTML
  报告）也只动 presenter。
"""
