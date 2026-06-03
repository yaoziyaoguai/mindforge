import { describe, it, expect } from "vitest";
import { t } from "../lib/i18n";

describe("SetupPage Logic", () => {
  it("should not use Ready for unverified status", () => {
    expect(t("setup.provider_readiness_ready", "zh")).toBe("配置已保存");
    expect(t("setup.provider_readiness_ready", "en")).toBe("Configured");
    expect(t("setup.status_ready", "zh")).toBe("配置已保存");
    expect(t("setup.status_ready", "en")).toBe("Configured");
  });

  it("should clarify that configuration check does not call real LLM", () => {
    expect(t("setup.guide_validate_tooltip", "zh")).toContain("不会调用真实模型");
  });

  it("should provide base_url validation warning", () => {
    expect(t("setup.validation.base_url_invalid", "zh")).toContain("不要包含 /chat/completions");
  });
});
