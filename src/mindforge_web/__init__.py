"""MindForge Local Console Web adapter package.

中文学习型说明：`mindforge_web` 是展示/控制层，不是新的业务核心。它可以
编排 Web 场景，但所有审批、recall、provider readiness、vault/card 读取
都必须复用 `mindforge` 现有 service / policy / storage。
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
