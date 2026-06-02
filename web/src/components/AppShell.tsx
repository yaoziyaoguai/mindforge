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
    <div className="flex min-h-screen" style={{ background: "var(--mf-surface-alt)" }}>
      <Sidebar path={path} onNavigate={onNavigate} providerState={safety?.provider_state} />
      <div className="flex min-w-0 flex-1 flex-col rounded-tl-2xl bg-white shadow-xl ring-1 ring-black/5" style={{ background: "var(--mf-surface)" }}>
        <SafetyBar safety={safety} onNavigate={onNavigate} />
        <main className="mx-auto w-full max-w-5xl flex-1 px-10 py-10">
          {children}
        </main>
      </div>
    </div>
  );
}
