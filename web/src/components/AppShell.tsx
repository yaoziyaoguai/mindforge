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
    <div className="flex min-h-screen" style={{ background: "var(--mf-bg)" }}>
      <Sidebar path={path} onNavigate={onNavigate} providerState={safety?.provider_state} />
      <div className="flex min-w-0 flex-1 flex-col">
        <SafetyBar safety={safety} onNavigate={onNavigate} />
        <main className="mx-auto w-full max-w-5xl flex-1 px-8 py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
