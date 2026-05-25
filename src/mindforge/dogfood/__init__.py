"""v3.4 Dogfood Scenario Automation — 本地知识工作台自动化验证。

中文学习型说明：模拟 import → ai_draft → review → approve → graph/search →
export → report 的完整知识生命周期，验证所有环节正确工作。

纯 fake 数据，不调用真实 LLM，不处理真实私人资料，不写真实 Obsidian vault。
"""

from mindforge.dogfood.scenario_runner import (
    ScenarioResult,
    ScenarioStep,
    ScenarioConfig,
    run_dogfood_scenario,
)

__all__ = [
    "ScenarioResult",
    "ScenarioStep",
    "ScenarioConfig",
    "run_dogfood_scenario",
]
