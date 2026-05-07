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
    <div className="flex min-h-screen bg-surface">
      <Sidebar path={path} onNavigate={onNavigate} />
      <div className="flex min-w-0 flex-1 flex-col">
        <SafetyBar safety={safety} />
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-6">{children}</main>
      </div>
    </div>
  );
}
