"""Processing run persistence and worker — core layer.

中文学习型说明：此包包含 ProcessingRun 的持久化、查询和 worker 执行逻辑。
这些是 core 层（src/mindforge/）的一等公民，不依赖 web 层（src/mindforge_web/）。
Web 层的 processing_run_service 是对此包的 thin re-export shim。
"""
