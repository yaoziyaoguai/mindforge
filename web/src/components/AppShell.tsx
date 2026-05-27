import type { ReactNode } from "react";
import type { SafetySummary } from "../api/types";
import { Breadcrumb } from "./Breadcrumb";
import { OnboardingHint } from "./OnboardingHint";
import { SafetyBar } from "./SafetyBar";
import { Sidebar } from "./Sidebar";

const PAGE_KEY_MAP: Record<string, string> = {
  "/": "home",
  "/setup": "setup",
  "/sources": "sources",
  "/drafts": "review",
  "/review": "review",
  "/library": "library",
  "/recall": "recall",
  "/search": "recall",
  "/wiki": "wiki",
  "/export": "export",
};

export function AppShell({
  path,
  safety,
  children,
  onNavigate,
}: {
  path: string;
  safety?: SafetySummary | null;
  children: ReactNode;
  onNavigate: (href: string) => void;
}) {
  const pageKey = PAGE_KEY_MAP[path] || "";

  return (
    <div className="flex min-h-screen" style={{ background: "var(--mf-bg)" }}>
      <Sidebar path={path} onNavigate={onNavigate} />
      <div className="flex min-w-0 flex-1 flex-col">
        <SafetyBar safety={safety} />
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-6">
          <Breadcrumb path={path} />
          {pageKey && <OnboardingHint pageKey={pageKey} />}
          {children}
        </main>
      </div>
    </div>
  );
}
