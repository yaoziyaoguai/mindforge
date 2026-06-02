import type { ReactNode } from "react";
import type { SafetySummary } from "../api/types";
import { SafetyBar } from "./SafetyBar";
import { Sidebar } from "./Sidebar";

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
  return (
    <div className="flex min-h-screen" style={{ background: "var(--mf-app-bg)" }}>
      <Sidebar path={path} onNavigate={onNavigate} providerState={safety?.provider_state} />
      <div
        className="flex min-w-0 flex-1 flex-col rounded-tl-[28px] shadow-xl ring-1 ring-black/5"
        style={{
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.94) 0%, rgba(251,251,255,0.98) 100%)",
          boxShadow: "var(--mf-shadow-card)",
        }}
      >
        <SafetyBar safety={safety} onNavigate={onNavigate} />
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 pb-12 pt-4 md:px-10 lg:px-12">
          {children}
        </main>
      </div>
    </div>
  );
}
