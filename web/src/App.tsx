import { useEffect, useState } from "react";
import { getConfigStatus } from "./api/config";
import { getDrafts } from "./api/drafts";
import { getHomeStatus } from "./api/home";
import { getSources } from "./api/sources";
import type { ConfigStatusResponse, DraftsResponse, HomeStatusResponse, SafetySummary, SourcesResponse } from "./api/types";
import { AppShell } from "./components/AppShell";
import { ErrorState } from "./components/ErrorState";
import { HomePage } from "./pages/HomePage";
import { SetupPage } from "./pages/SetupPage";
import { SourcesPage } from "./pages/SourcesPage";
import { DraftsPage } from "./pages/DraftsPage";
import { RecallPage } from "./pages/RecallPage";

type PageData = {
  home?: HomeStatusResponse;
  config?: ConfigStatusResponse;
  sources?: SourcesResponse;
  drafts?: DraftsResponse;
};

export default function App() {
  const [path, setPath] = useState(window.location.pathname);
  const [data, setData] = useState<PageData>({});
  const [safety, setSafety] = useState<SafetySummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  function navigate(href: string) {
    window.history.pushState({}, "", href);
    setPath(window.location.pathname);
  }

  async function load() {
    setError(null);
    try {
      const home = await getHomeStatus();
      setSafety(home.safety);
      const next: PageData = { home };
      if (path.startsWith("/setup")) next.config = await getConfigStatus();
      if (path.startsWith("/sources")) next.sources = await getSources();
      if (path.startsWith("/drafts")) next.drafts = await getDrafts();
      setData(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load MindForge status");
    }
  }

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    void load();
  }, [path]);

  let content = error ? <ErrorState message={error} /> : null;
  if (!content && path.startsWith("/setup") && data.config) content = <SetupPage data={data.config} />;
  if (!content && path.startsWith("/sources") && data.sources) content = <SourcesPage data={data.sources} />;
  if (!content && path.startsWith("/drafts") && data.drafts) content = <DraftsPage data={data.drafts} onRefresh={load} />;
  if (!content && path.startsWith("/recall")) content = <RecallPage />;
  if (!content && data.home) content = <HomePage data={data.home} onNavigate={navigate} />;
  if (!content) content = <div className="text-sm text-muted">Loading...</div>;

  return (
    <AppShell path={path} safety={safety} onNavigate={navigate}>
      {content}
    </AppShell>
  );
}
