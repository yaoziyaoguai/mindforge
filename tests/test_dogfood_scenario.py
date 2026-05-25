"""v3.4 — Dogfood 场景自动化测试。

验证 ScenarioRunner 的完整生命周期：
    workspace_setup → card_scan → graph_detection → report_generation → export

纯 fake 数据，不调用真实 LLM，不处理真实私人资料。
"""

from __future__ import annotations

import tempfile

from mindforge.dogfood import (
    ScenarioConfig,
    ScenarioStep,
    run_dogfood_scenario,
)


class TestScenarioRunner:
    """验证场景执行器的核心行为。"""

    def test_runs_all_steps_successfully(self):
        """标准配置下所有步骤应通过。"""
        tmp = tempfile.mkdtemp(prefix="dogfood_test_")
        result = run_dogfood_scenario(tmp)
        assert result.all_passed
        assert result.total_cards == 5
        assert result.approved_count == 3
        assert result.draft_count == 1
        assert result.trashed_count == 1

    def test_approval_rate_correct(self):
        """确认率计算正确：3/5 = 0.6。"""
        tmp = tempfile.mkdtemp(prefix="dogfood_test_")
        result = run_dogfood_scenario(tmp)
        assert result.approval_rate == 0.6

    def test_graph_detection_finds_edges(self):
        """图谱检测应找到关系边。"""
        tmp = tempfile.mkdtemp(prefix="dogfood_test_")
        result = run_dogfood_scenario(tmp)
        assert result.graph_relation_count > 0, "应检测到至少一些图谱关系"
        assert result.community_count > 0, "应检测到至少一个社区"

    def test_all_required_steps_present(self):
        """结果应包含所有必需的步骤。"""
        tmp = tempfile.mkdtemp(prefix="dogfood_test_")
        result = run_dogfood_scenario(tmp)
        step_names = {s.step_name for s in result.steps}
        assert "workspace_setup" in step_names
        assert "card_scan" in step_names
        assert "graph_detection" in step_names
        assert "report_generation" in step_names

    def test_summary_contains_key_metrics(self):
        tmp = tempfile.mkdtemp(prefix="dogfood_test_")
        result = run_dogfood_scenario(tmp)
        assert "5 cards" in result.summary or "5 张" in result.summary
        assert "60%" in result.summary or "60%" in result.summary

    def test_duration_fields_populated(self):
        """各步骤和总耗时应有值。"""
        tmp = tempfile.mkdtemp(prefix="dogfood_test_")
        result = run_dogfood_scenario(tmp)
        assert result.total_duration_ms > 0
        for step in result.steps:
            if step.status != "skipped":
                assert step.duration_ms >= 0

    def test_no_export_by_default(self):
        """默认配置下导出应跳过。"""
        tmp = tempfile.mkdtemp(prefix="dogfood_test_")
        result = run_dogfood_scenario(tmp)
        export_step = next(s for s in result.steps if s.step_name == "export_verification")
        assert export_step.status == "skipped"

    def test_empty_workspace_creates_and_runs(self):
        """run_dogfood_scenario 内部调用 build_sample_workspace 创建工作区。"""
        tmp = tempfile.mkdtemp(prefix="dogfood_empty_")
        result = run_dogfood_scenario(tmp)
        # build_sample_workspace 总是成功创建 workspace，因此后续步骤应通过
        assert result.all_passed

    def test_deterministic_same_input_same_output(self):
        """相同场景应产生一致结果。"""
        tmp1 = tempfile.mkdtemp(prefix="dogfood_det_")
        tmp2 = tempfile.mkdtemp(prefix="dogfood_det_")
        r1 = run_dogfood_scenario(tmp1)
        r2 = run_dogfood_scenario(tmp2)
        assert r1.total_cards == r2.total_cards
        assert r1.approved_count == r2.approved_count
        assert r1.approval_rate == r2.approval_rate
        assert r1.all_passed == r2.all_passed
        # 图边数应一致（确定性算法）
        assert r1.graph_relation_count == r2.graph_relation_count
        assert r1.community_count == r2.community_count


class TestScenarioConfig:
    """验证场景配置选项。"""

    def test_graph_disabled_config(self):
        """禁用图谱时步骤应跳过。"""
        tmp = tempfile.mkdtemp(prefix="dogfood_nograph_")
        config = ScenarioConfig(run_graph=False)
        result = run_dogfood_scenario(tmp, config=config)
        graph_step = next(s for s in result.steps if s.step_name == "graph_detection")
        assert graph_step.status == "skipped"
        assert result.graph_relation_count == 0

    def test_export_enabled_config(self):
        """启用导出时步骤应执行。"""
        tmp = tempfile.mkdtemp(prefix="dogfood_export_")
        config = ScenarioConfig(run_export=True)
        result = run_dogfood_scenario(tmp, config=config)
        export_step = next(s for s in result.steps if s.step_name == "export_verification")
        assert export_step.status != "skipped"


class TestScenarioResult:
    """验证 ScenarioResult 数据结构。"""

    def test_scenario_result_is_frozen(self):
        """ScenarioResult 应为不可变对象。"""
        tmp = tempfile.mkdtemp(prefix="dogfood_frozen_")
        result = run_dogfood_scenario(tmp)
        with __import__("pytest").raises(Exception):
            result.total_cards = 999  # type: ignore[misc]

    def test_scenario_step_is_frozen(self):
        """ScenarioStep 应为不可变对象。"""
        step = ScenarioStep("test", "passed", 100, "detail")
        with __import__("pytest").raises(Exception):
            step.status = "failed"  # type: ignore[misc]


class TestCLI:
    """验证 CLI 入口点。"""

    def test_cli_entry_exists(self):
        from mindforge.dogfood.scenario_runner import run_cli
        assert callable(run_cli)

    def test_module_imports_cleanly(self):
        """mindforge.dogfood 模块应可正常导入。"""
        import mindforge.dogfood
        assert hasattr(mindforge.dogfood, "run_dogfood_scenario")
        assert hasattr(mindforge.dogfood, "ScenarioResult")
        assert hasattr(mindforge.dogfood, "ScenarioConfig")
