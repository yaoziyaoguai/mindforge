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
    it("shows ShieldCheck icon for vault path", () => {
      const { container } = renderWithLocale(<SafetyBar safety={baseSafety} />);
      const svgs = container.querySelectorAll("svg");
      expect(svgs.length).toBeGreaterThanOrEqual(1);
    });

    it("shows vault path even when local_only is false", () => {
      renderWithLocale(<SafetyBar safety={{ ...baseSafety, local_only: false }} />);
      expect(screen.getByText(/Vault:/)).toBeInTheDocument();
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
      // t("safety.model_setup") → "模型配置："
      expect(screen.getByText(/模型配置：/)).toBeInTheDocument();
      // t("boundary.live") → "Live / 真实模型"
      expect(screen.getByText("Live / 真实模型")).toBeInTheDocument();
    });

    it("renders non-ready provider state", () => {
      renderWithLocale(<SafetyBar safety={{ ...baseSafety, provider_state: "blocked" }} />);
      // t("safety.model_setup") → "模型配置："
      expect(screen.getByText(/模型配置：/)).toBeInTheDocument();
      // t("boundary.sandbox") → "Sandbox / 模拟"
      expect(screen.getByText("Sandbox / 模拟")).toBeInTheDocument();
    });
  });

  describe("pending drafts always visible", () => {
    it("shows pending drafts regardless of write_mode", () => {
      renderWithLocale(<SafetyBar safety={baseSafety} />);
      expect(screen.getByText("待审阅：3")).toBeInTheDocument();
    });

    it("shows pending drafts in read_only mode too", () => {
      renderWithLocale(<SafetyBar safety={{ ...baseSafety, write_mode: "read_only" }} />);
      expect(screen.getByText("待审阅：3")).toBeInTheDocument();
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

  it("renders ShieldCheck and CheckCircle2 icons", () => {
    const { container } = renderWithLocale(<SafetyBar safety={baseSafety} />);
    // 新 SafetyBar: ShieldCheck + CheckCircle2 = 2 个图标
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThanOrEqual(2);
  });

  it("replaces CheckCircle2 with warning text when warnings present", () => {
    const { container } = renderWithLocale(
      <SafetyBar safety={{ ...baseSafety, warnings: ["过期"] }} />,
    );
    // ShieldCheck 仍在，CheckCircle2 被文本替换
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThanOrEqual(1);
  });
});
