import { useEffect, useState } from "react";
import { getConfigStatus } from "./api/config";
import { getDrafts } from "./api/drafts";
import { getHomeStatus } from "./api/home";
import { getLibraryCards, getWorkflowSummary } from "./api/library";
import { getSources } from "./api/sources";
import type { ConfigStatusResponse, DraftsResponse, HomeStatusResponse, LibraryCardsResponse, SafetySummary, SourcesResponse, WorkflowSummaryResponse } from "./api/types";
import { AppShell } from "./components/AppShell";
import { ErrorState } from "./components/ErrorState";
import { LoadingSkeleton } from "./components/LoadingSkeleton";
import { LocaleProvider } from "./lib/i18n";
import { HomePage } from "./pages/HomePage";
import { SetupPage } from "./pages/SetupPage";
import { SourcesPage } from "./pages/SourcesPage";
import { DraftsPage } from "./pages/DraftsPage";
import { ReviewPage } from "./pages/ReviewPage";
import { RecallPage } from "./pages/RecallPage";
import { LibraryPage } from "./pages/LibraryPage";
import { HealthPage } from "./pages/HealthPage";
import { TrashPage } from "./pages/TrashPage";
import { WikiPage } from "./pages/WikiPage";
import { DogfoodPage } from "./pages/DogfoodPage";
import { GraphPage } from "./pages/GraphPage";
import { SensemakingPage } from "./pages/SensemakingPage";
import { ExportPage } from "./pages/ExportPage";
import { UsageReportPage } from "./pages/UsageReportPage";

type PageData = {
  home?: HomeStatusResponse;
  config?: ConfigStatusResponse;
  sources?: SourcesResponse;
  drafts?: DraftsResponse;
  library?: LibraryCardsResponse;
  workflow?: WorkflowSummaryResponse;
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
      if (path === "/" || path.startsWith("/library") || path.startsWith("/sources")) {
        next.workflow = await getWorkflowSummary();
      }
      if (path.startsWith("/setup")) next.config = await getConfigStatus();
      if (path.startsWith("/sources")) next.sources = await getSources();
      if (path.startsWith("/drafts")) next.drafts = await getDrafts();
      if (path.startsWith("/review")) next.drafts = await getDrafts();
      if (path.startsWith("/library")) next.library = await getLibraryCards();
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
  if (!content && path.startsWith("/setup") && data.config) content = <SetupPage data={data.config} onRefresh={load} />;
  if (!content && path.startsWith("/sources") && data.sources) content = <SourcesPage data={data.sources} onNavigate={navigate} onRefresh={load} providerState={data.home?.safety.provider_state} />;
  if (!content && path.startsWith("/review") && data.drafts) content = <ReviewPage data={data.drafts} onRefresh={load} providerState={data.home?.safety.provider_state} />;
  if (!content && path.startsWith("/drafts") && data.drafts) content = <DraftsPage data={data.drafts} onRefresh={load} onNavigate={navigate} providerState={data.home?.safety.provider_state} />;
  if (!content && path.startsWith("/library") && data.library) content = <LibraryPage data={data.library} onRefresh={load} />;
  if (!content && (path.startsWith("/recall") || path.startsWith("/search"))) content = <RecallPage onNavigate={navigate} />;
  if (!content && path.startsWith("/health")) content = <HealthPage onNavigate={navigate} />;
  if (!content && path.startsWith("/trash")) content = <TrashPage onRefresh={load} />;
  if (!content && path.startsWith("/wiki")) content = <WikiPage />;
  if (!content && path.startsWith("/usage-report")) content = <UsageReportPage />;
  if (!content && path.startsWith("/dogfood")) content = <DogfoodPage onNavigate={navigate} />;
  if (!content && path.startsWith("/graph")) content = <GraphPage onNavigateBack={() => navigate("/library")} />;
  if (!content && path.startsWith("/sensemaking")) content = <SensemakingPage onNavigateBack={() => navigate("/library")} />;
  if (!content && path.startsWith("/export")) content = <ExportPage />;
  if (!content && data.home) content = <HomePage data={data.home} workflow={data.workflow} onNavigate={navigate} />;
  if (!content) {
    const variant = path.startsWith("/wiki") ? "wiki" : path.startsWith("/library") ? "library" : path.startsWith("/review") ? "drafts" : path.startsWith("/drafts") ? "drafts" : path.startsWith("/setup") ? "setup" : path.startsWith("/sources") ? "sources" : path.startsWith("/recall") || path.startsWith("/search") ? "search" : path.startsWith("/health") ? "health" : path.startsWith("/trash") ? "trash" : path.startsWith("/dogfood") ? "dogfood" : path.startsWith("/usage-report") ? "usage-report" : path.startsWith("/export") ? "default" : path.startsWith("/graph") ? "default" : "default";
    content = <LoadingSkeleton variant={variant as "default" | "wiki" | "library" | "drafts" | "search" | "sources" | "health" | "trash" | "setup" | "dogfood"} />;
  }

  return (
    <LocaleProvider>
      <AppShell path={path} safety={safety} onNavigate={navigate}>
        {content}
      </AppShell>
    </LocaleProvider>
  );
}
