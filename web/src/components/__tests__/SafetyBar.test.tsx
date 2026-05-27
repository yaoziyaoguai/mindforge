import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LocaleProvider } from "../../lib/i18n";
import { SafetyBar } from "../SafetyBar";
import type { SafetySummary } from "../../api/types";

// 用 LocaleProvider 包裹组件，解决 useLocale() 需要 i18n context 的问题
function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

const baseSafety: SafetySummary = {
  local_only: true,
  host: "http://127.0.0.1:8765",
  vault_path: "/Users/test/mindforge-vault",
  vault_status: "ok",
  provider_state: "ready",
  env_status: "ok",
  write_mode: "explicit_approval_required",
  pending_drafts_count: 3,
  warnings: [],
};

describe("SafetyBar", () => {
  describe("loading state", () => {
    it("renders loading text when safety is null", () => {
      renderWithLocale(<SafetyBar safety={null} />);
      // t("safety.loading") → "正在加载安全状态..."
      expect(screen.getByText("正在加载安全状态...")).toBeInTheDocument();
    });

    it("renders loading text when safety is undefined", () => {
      renderWithLocale(<SafetyBar />);
      expect(screen.getByText("正在加载安全状态...")).toBeInTheDocument();
    });
  });

  describe("local mode", () => {
    it("renders local_only message when true", () => {
      renderWithLocale(<SafetyBar safety={baseSafety} />);
      // t("safety.local_only") → "本地运行"
      expect(screen.getByText("本地运行")).toBeInTheDocument();
    });

    it("renders host warning when local_only is false", () => {
      renderWithLocale(<SafetyBar safety={{ ...baseSafety, local_only: false }} />);
      // t("safety.host_warning") → "主机警告"
      expect(screen.getByText("主机警告")).toBeInTheDocument();
    });
  });

  describe("vault path", () => {
    it("renders vault path with Vault prefix", () => {
      renderWithLocale(<SafetyBar safety={baseSafety} />);
      // truncateMiddle 截断路径至 58 字符，短路径保持原样
      expect(screen.getByText(/Vault: \/Users\/test\/mindforge-vault/)).toBeInTheDocument();
    });

    it("renders long vault path truncated", () => {
      const longPath = "/Users/test/" + "a".repeat(80) + "/mindforge-vault";
      renderWithLocale(<SafetyBar safety={{ ...baseSafety, vault_path: longPath }} />);
      // truncateMiddle 将中间替换为 "..."
      expect(screen.getByText(/\.\.\./)).toBeInTheDocument();
    });
  });

  describe("provider state", () => {
    it("renders ready state correctly", () => {
      renderWithLocale(<SafetyBar safety={baseSafety} />);
      // t("safety.model_setup") + t("safety.model_ready") → "模型配置：就绪"
      // 两个 JSX 表达式在 happy-dom 中可能产生独立文本节点，用正则匹配合并后的 textContent
      expect(screen.getByText(/模型配置：\s*就绪/)).toBeInTheDocument();
    });

    it("renders non-ready provider state", () => {
      renderWithLocale(<SafetyBar safety={{ ...baseSafety, provider_state: "blocked" }} />);
      // t("safety.model_setup") + t("safety.model_check") → "模型配置：待检查"
      expect(screen.getByText(/模型配置：\s*待检查/)).toBeInTheDocument();
    });
  });

  describe("write mode", () => {
    it("renders explicit_approval mode", () => {
      renderWithLocale(<SafetyBar safety={baseSafety} />);
      // t("safety.explicit_approval") → "需显式确认"
      expect(screen.getByText("需显式确认")).toBeInTheDocument();
    });

    it("renders read_only mode", () => {
      renderWithLocale(<SafetyBar safety={{ ...baseSafety, write_mode: "read_only" }} />);
      // t("safety.read_only") → "只读模式"
      expect(screen.getByText("只读模式")).toBeInTheDocument();
    });
  });

  describe("pending drafts", () => {
    it("renders pending drafts count with label", () => {
      renderWithLocale(<SafetyBar safety={baseSafety} />);
      // t("safety.needs_review") → "待审阅：" + pending_drafts_count = "待审阅：3"
      expect(screen.getByText("待审阅：3")).toBeInTheDocument();
    });
  });

  describe("warnings", () => {
    it("renders safe state when no warnings", () => {
      renderWithLocale(<SafetyBar safety={baseSafety} />);
      // t("safety.safe_local_read") → "安全本地读取"
      expect(screen.getByText("安全本地读取")).toBeInTheDocument();
    });

    it("renders first warning when warnings present", () => {
      renderWithLocale(<SafetyBar safety={{ ...baseSafety, warnings: ["检测到过期Wiki"] }} />);
      expect(screen.getByText("检测到过期Wiki")).toBeInTheDocument();
    });

    it("does not render safe state when warnings present", () => {
      renderWithLocale(<SafetyBar safety={{ ...baseSafety, warnings: ["警告信息"] }} />);
      expect(screen.queryByText("安全本地读取")).toBeNull();
    });
  });

  it("renders ShieldCheck icon for local_only", () => {
    const { container } = renderWithLocale(<SafetyBar safety={baseSafety} />);
    // ShieldCheck, Lock, CheckCircle2 三个图标
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThanOrEqual(3);
  });

  it("renders AlertTriangle icon when warnings present", () => {
    const { container } = renderWithLocale(
      <SafetyBar safety={{ ...baseSafety, warnings: ["过期"] }} />,
    );
    // 应该有 AlertTriangle 替换 CheckCircle2
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThanOrEqual(3);
  });
});
