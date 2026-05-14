"""Provider runtime defaults shared by config loading, Web Setup, and LLM calls.

中文学习型说明：这些常量描述真实模型调用的运行边界，不属于 YAML schema
本身。把它们放在独立模块，可以避免 ``config.py`` 继续吞入 provider runtime
语义，同时保持 config loader / Web Setup / provider fallback 使用同一套默认值。
"""

DEFAULT_PROVIDER_TIMEOUT_SECONDS = 120
DEFAULT_PROVIDER_MAX_RETRIES = 1


__all__ = [
    "DEFAULT_PROVIDER_TIMEOUT_SECONDS",
    "DEFAULT_PROVIDER_MAX_RETRIES",
]
