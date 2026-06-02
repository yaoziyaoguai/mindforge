import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Brain, Loader2 } from "lucide-react";
import { fetchSensemaking } from "../api/graph";
import type { SensemakingResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

type ViewMode = "bridge" | "orphan" | "evidence" | "influence" | "evolution" | "community";

interface ViewModeOption {
  mode: ViewMode;
  icon: string;
  labelKey: string;
  descKey: string;
}

const VIEW_MODES: ViewModeOption[] = [
  { mode: "bridge", icon: "🌉", labelKey: "sensemaking.bridge_nodes", descKey: "sensemaking.bridge_desc" },
  { mode: "orphan", icon: "🏝️", labelKey: "sensemaking.orphan_islands", descKey: "sensemaking.orphan_desc" },
  { mode: "evidence", icon: "🔍", labelKey: "sensemaking.evidence_trail", descKey: "sensemaking.evidence_desc" },
  { mode: "influence", icon: "🌐", labelKey: "sensemaking.source_influence", descKey: "sensemaking.influence_desc" },
  { mode: "evolution", icon: "🌱", labelKey: "sensemaking.card_evolution", descKey: "sensemaking.evolution_desc" },
  { mode: "community", icon: "👥", labelKey: "sensemaking.community_subgraphs", descKey: "sensemaking.community_desc" },
];

interface Props {
  initialCardId?: string;
  onNavigateBack?: () => void;
}

export function SensemakingPage({ initialCardId, onNavigateBack }: Props) {
  const { t } = useLocale();

  const urlCardId = new URLSearchParams(window.location.search).get("card") ?? undefined;
  const effectiveCardId = initialCardId ?? urlCardId;

  const [viewMode, setViewMode] = useState<ViewMode>("community");
  const [analysis, setAnalysis] = useState<SensemakingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputCardId, setInputCardId] = useState(effectiveCardId ?? "");
  const [autoAnalyzed, setAutoAnalyzed] = useState(false);
  const [selectedTrailIndex, setSelectedTrailIndex] = useState<number | null>(null);

  useEffect(() => {
    if (effectiveCardId && !autoAnalyzed) {
      setAutoAnalyzed(true);
      setInputCardId(effectiveCardId);
      runAnalysis(effectiveCardId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveCardId]);

  const runAnalysis = useCallback((overrideId?: string) => {
    const id = (overrideId ?? inputCardId).trim();
    if (!id) return;
    setLoading(true);
    setError(null);
    fetchSensemaking(id)
      .then((result) => {
        setAnalysis(result);
        setSelectedTrailIndex(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unknown error");
        setAnalysis(null);
      })
      .finally(() => setLoading(false));
  }, [inputCardId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") runAnalysis();
  };

  return (
    <div className="space-y-4">
      {/* v4.2.1: LAB/INTERNAL warning banner — styled with main web tokens */}
      <div className="rounded-lg border p-4" style={{ borderColor: "var(--mf-warning)/30", background: "var(--mf-accent-faint)" }}>
        <div className="text-sm font-semibold" style={{ color: "var(--mf-warning)" }}>
          LAB / INTERNAL — 实验性分析功能
        </div>
        <div className="mt-2 text-xs leading-relaxed" style={{ color: "var(--mf-text-secondary)" }}>
          <p className="mb-1">本页面提供的是基于确定性 heuristics 的实验性分析（BFS + 集合运算），不是成熟的 sensemaking 产品能力。</p>
          <ul className="ml-4 list-disc space-y-0.5">
            <li>BridgeNode: 简单社区交集计数，不涉及 centrality / modularity</li>
            <li>CardEvolutionPath: 按 card_id 排序，不代表真实时间演化</li>
            <li>SourceInfluencePath: 简单 BFS，不涉及 causal inference</li>
            <li>Evidence Trail: 集合交集匹配，仅供探索参考</li>
          </ul>
          <p className="mt-1">这不是 production sensemaking 功能。分析结果不应作为知识质量的权威依据。</p>
        </div>
      </div>

      {/* Header */}
      <div className="flex items-center gap-3">
        {onNavigateBack && (
          <button
            onClick={onNavigateBack}
            className="inline-flex items-center gap-1 rounded-md border border-line px-3 py-1.5 text-sm text-muted hover:text-ink"
          >
            <ArrowLeft size={16} />
            {t("graph.back_to_library")}
          </button>
        )}
        <Brain size={20} className="text-[var(--mf-accent)]" />
        <h1 className="text-lg font-semibold text-ink">
          {t("sensemaking.title")}
        </h1>
        <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold" style={{ background: "var(--mf-accent-soft)", color: "var(--mf-accent)" }}>
          LAB
        </span>
      </div>

      {/* Search bar */}
      <div className="flex gap-2">
        <input
          type="text"
          value={inputCardId}
          onChange={(e) => setInputCardId(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="card ID or filename..."
          className="flex-1 rounded-md border border-line px-3 py-2 text-sm text-ink placeholder:text-muted"
        />
        <button
          onClick={() => runAnalysis()}
          disabled={loading || !inputCardId.trim()}
          className="rounded-md px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
          style={{ background: loading ? "var(--mf-text-tertiary)" : "var(--mf-accent)" }}
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : "Analyze"}
        </button>
      </div>

      {/* View mode tabs */}
      <div className="flex flex-wrap gap-1">
        {VIEW_MODES.map((vm) => (
          <button
            key={vm.mode}
            onClick={() => { setViewMode(vm.mode); setSelectedTrailIndex(null); }}
            title={t(vm.descKey)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
              viewMode === vm.mode
                ? "border-2 border-[var(--mf-accent)] text-[var(--mf-accent)]"
                : "border border-line text-muted hover:text-ink"
            }`}
            style={{ background: viewMode === vm.mode ? "var(--mf-accent-soft)" : "var(--mf-surface, #fff)" }}
          >
            {vm.icon} {t(vm.labelKey)}
          </button>
        ))}
      </div>

      {/* Content area */}
      {loading && (
        <div className="flex items-center justify-center py-16 text-sm text-muted">
          <Loader2 size={32} className="mb-2 animate-spin" />
          <p>{t("sensemaking.loading")}</p>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-[var(--mf-error)]/30 bg-[var(--mf-error)]/5 p-6 text-center text-sm" style={{ color: "var(--mf-error)" }}>
          <p>{t("sensemaking.load_failed")}: {error}</p>
        </div>
      )}

      {!loading && !error && analysis && (
        <div className="grid gap-4" style={{ gridTemplateColumns: selectedTrailIndex !== null ? "3fr 2fr" : "1fr" }}>
          {/* Main panel */}
          <div className="rounded-xl border border-line bg-panel p-5 shadow-subtle">
            {viewMode === "bridge" && <BridgeNodesView analysis={analysis} t={t} onCardClick={(id) => { setInputCardId(id); runAnalysis(id); }} />}
            {viewMode === "orphan" && <OrphanIslandsView analysis={analysis} t={t} onCardClick={(id) => { setInputCardId(id); runAnalysis(id); }} />}
            {viewMode === "evidence" && (
              <EvidenceTrailView
                analysis={analysis} t={t}
                onSelectTrail={setSelectedTrailIndex}
                selectedIndex={selectedTrailIndex}
              />
            )}
            {viewMode === "influence" && <SourceInfluenceView analysis={analysis} t={t} onCardClick={(id) => { setInputCardId(id); runAnalysis(id); }} />}
            {viewMode === "evolution" && <CardEvolutionView analysis={analysis} t={t} onCardClick={(id) => { setInputCardId(id); runAnalysis(id); }} />}
            {viewMode === "community" && <CommunitySubgraphsView analysis={analysis} t={t} onCardClick={(id) => { setInputCardId(id); runAnalysis(id); }} />}
          </div>

          {/* Evidence trail detail panel */}
          {selectedTrailIndex !== null && viewMode === "evidence" && analysis.evidence_trails[selectedTrailIndex] && (
            <div className="rounded-xl border border-line bg-panel shadow-subtle overflow-hidden">
              <EvidenceTrailDetail
                trail={analysis.evidence_trails[selectedTrailIndex]}
                t={t}
                onClose={() => setSelectedTrailIndex(null)}
              />
            </div>
          )}
        </div>
      )}

      {!loading && !error && !analysis && (
        <div className="flex items-center justify-center py-16 text-center text-sm text-muted">
          <div>
            <p>输入卡片 ID 以探索实验性知识图谱分析（LAB / INTERNAL）。</p>
            <p className="mt-1 text-xs">所有分析基于确定性 heuristics，不涉及 LLM / embedding / vector DB。</p>
          </div>
        </div>
      )}

      {/* v4.0 badge */}
      {analysis && (
        <div className="text-center text-xs text-muted">
          {analysis.total_cards_analyzed} cards analyzed · center: {analysis.center_card_title}
        </div>
      )}
    </div>
  );
}

/* ── Bridge Nodes ─────────────────────────────── */

function BridgeNodesView({
  analysis, t, onCardClick,
}: { analysis: SensemakingResponse; t: (k: string) => string; onCardClick: (id: string) => void }) {
  const bridges = analysis.bridge_nodes;
  if (bridges.length === 0) {
    return <EmptyState icon="🌉" message={t("sensemaking.no_bridge")} />;
  }
  return (
    <div>
      <h2 className="mb-3 text-base font-semibold text-ink">
        {t("sensemaking.bridge_nodes")} ({bridges.length})
      </h2>
      <div className="flex flex-col gap-2">
        {bridges.map((b) => (
          <div
            key={b.card_id}
            className="rounded-lg border border-line bg-panel p-4"
          >
            <div className="flex justify-between items-center">
              <button
                onClick={() => onCardClick(b.card_id)}
                className="text-sm font-semibold text-[var(--mf-accent)] underline underline-offset-2"
              >
                {b.card_title}
              </button>
              <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold text-white" style={{ background: "var(--mf-accent)" }}>
                {b.community_count} communities
              </span>
            </div>
            <div className="mt-1 text-xs" style={{ color: "var(--mf-text-tertiary)" }}>
              {t("sensemaking.connecting_communities")}: {b.connecting_communities.slice(0, 5).join(", ")}
              {b.connecting_communities.length > 5 && ` +${b.connecting_communities.length - 5} more`}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Orphan Islands ───────────────────────────── */

function OrphanIslandsView({
  analysis, t, onCardClick,
}: { analysis: SensemakingResponse; t: (k: string) => string; onCardClick: (id: string) => void }) {
  const orphans = analysis.orphan_islands;
  if (orphans.length === 0) {
    return <EmptyState icon="🏝️" message={t("sensemaking.no_orphan")} />;
  }
  const trueOrphans = orphans.filter((o) => o.is_true_orphan);
  const islands = orphans.filter((o) => !o.is_true_orphan);
  return (
    <div>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
        {t("sensemaking.orphan_islands")} ({orphans.length})
      </h2>
      {trueOrphans.length > 0 && (
        <SectionBadge label={t("sensemaking.true_orphan")} count={trueOrphans.length} />
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {trueOrphans.map((o) => (
          <div key={o.card_ids[0]} style={{
            border: "1px solid #fecaca", borderRadius: "8px", padding: "0.6rem 1rem",
            background: "#fef2f2",
          }}>
            {o.card_ids.map((cid, i) => (
              <button
                key={cid}
                onClick={() => onCardClick(cid)}
                style={{
                  background: "none", border: "none", color: "#dc2626", cursor: "pointer",
                  fontWeight: 500, fontSize: "0.85rem", padding: 0, display: "block",
                  textDecoration: "underline", textUnderlineOffset: "2px",
                }}
              >
                {o.card_titles[i] || cid}
              </button>
            ))}
          </div>
        ))}
      </div>
      {islands.length > 0 && (
        <>
          <SectionBadge label={t("sensemaking.island_group")} count={islands.length} />
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {islands.map((o, idx) => (
              <div key={idx} style={{
                border: "1px solid var(--border, #e2e8f0)", borderRadius: "8px",
                padding: "0.6rem 1rem", background: "var(--bg-secondary, #fff)",
              }}>
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted, #94a3b8)", marginBottom: "0.25rem" }}>
                  {o.size} cards
                </div>
                {o.card_ids.map((cid, i) => (
                  <button
                    key={cid}
                    onClick={() => onCardClick(cid)}
                    style={{
                      background: "none", border: "none", color: "var(--accent, #6366f1)",
                      cursor: "pointer", fontWeight: 500, fontSize: "0.85rem", padding: 0,
                      display: "block", textDecoration: "underline", textUnderlineOffset: "2px",
                    }}
                  >
                    {o.card_titles[i] || cid}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/* ── Evidence Trail ────────────────────────────── */

function EvidenceTrailView({
  analysis, t, onSelectTrail, selectedIndex,
}: {
  analysis: SensemakingResponse; t: (k: string) => string;
  onSelectTrail: (i: number | null) => void; selectedIndex: number | null;
}) {
  const trails = analysis.evidence_trails;
  if (trails.length === 0) {
    return <EmptyState icon="🔍" message={t("sensemaking.no_trail")} />;
  }
  return (
    <div>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
        {t("sensemaking.evidence_trail")} ({trails.length})
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {trails.map((trail, i) => (
          <div
            key={`${trail.source_id}-${trail.target_id}`}
            onClick={() => onSelectTrail(selectedIndex === i ? null : i)}
            style={{
              border: selectedIndex === i ? "2px solid var(--accent, #6366f1)" : "1px solid var(--border, #e2e8f0)",
              borderRadius: "8px", padding: "0.75rem 1rem", cursor: "pointer",
              background: selectedIndex === i ? "var(--accent-light, #eef2ff)" : "var(--bg-secondary, #fff)",
              transition: "all 0.15s",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{trail.source_title}</span>
                <span style={{ margin: "0 0.5rem", color: "var(--text-muted, #94a3b8)" }}>→</span>
                <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{trail.target_title}</span>
              </div>
              <span style={{
                background: "var(--bg-tertiary, #f1f5f9)", borderRadius: "10px",
                padding: "0.15rem 0.5rem", fontSize: "0.7rem",
              }}>
                {trail.total_shared_entities} {t("sensemaking.shared_entities")}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EvidenceTrailDetail({
  trail, t, onClose,
}: {
  trail: NonNullable<SensemakingResponse["evidence_trails"]>[number];
  t: (k: string) => string; onClose: () => void;
}) {
  return (
    <div style={{
      flex: "0 0 340px", border: "1px solid var(--border, #e2e8f0)",
      borderRadius: "8px", padding: "1rem", background: "var(--bg-secondary, #fff)",
      maxHeight: "70vh", overflowY: "auto", position: "sticky", top: "1rem",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>{t("sensemaking.evidence_trail")}</h3>
        <button
          onClick={onClose}
          style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.2rem", lineHeight: 1, color: "var(--text-muted, #94a3b8)" }}
        >
          ×
        </button>
      </div>
      <div style={{ marginBottom: "0.75rem" }}>
        <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{trail.source_title}</div>
        <div style={{ color: "var(--text-muted, #94a3b8)", margin: "0.25rem 0" }}>↓ relation ↓</div>
        <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{trail.target_title}</div>
      </div>
      <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.5rem" }}>
        {t("sensemaking.shared_entities")} ({trail.total_shared_entities})
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
        {trail.trail_items.map((item, i) => (
          <div
            key={i}
            style={{
              padding: "0.4rem 0.6rem", borderRadius: "6px",
              background: "var(--bg-tertiary, #f8fafc)", fontSize: "0.8rem",
              borderLeft: "3px solid var(--accent, #6366f1)",
            }}
          >
            <span style={{
              fontSize: "0.65rem", fontWeight: 600, textTransform: "uppercase",
              color: "var(--accent, #6366f1)", marginRight: "0.5rem",
            }}>
              {item.evidence_type}
            </span>
            {item.description}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Source Influence ──────────────────────────── */

function SourceInfluenceView({
  analysis, t, onCardClick,
}: { analysis: SensemakingResponse; t: (k: string) => string; onCardClick: (id: string) => void }) {
  const inf = analysis.source_influence;
  if (!inf) return <EmptyState icon="🌐" message={t("sensemaking.no_influence")} />;
  return (
    <div>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
        {t("sensemaking.source_influence")}
      </h2>
      <div style={{
        border: "1px solid var(--border, #e2e8f0)", borderRadius: "8px",
        padding: "1rem", background: "var(--bg-secondary, #fff)", marginBottom: "0.75rem",
      }}>
        <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>{t("sensemaking.source")}: {inf.source_label}</div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted, #94a3b8)" }}>
          {t("sensemaking.total_reach")}: {inf.total_reach} cards
        </div>
      </div>

      <SectionBadge label={t("sensemaking.direct_cards")} count={inf.direct_cards.length} />
      <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", marginBottom: "1rem" }}>
        {inf.direct_cards.map((cid, i) => (
          <button
            key={cid}
            onClick={() => onCardClick(cid)}
            style={{
              background: "none", border: "none", color: "var(--accent, #6366f1)",
              cursor: "pointer", textAlign: "left", padding: "0.3rem 0.5rem",
              textDecoration: "underline", textUnderlineOffset: "2px", fontSize: "0.85rem",
            }}
          >
            {inf.direct_card_titles[i] || cid}
          </button>
        ))}
      </div>

      <SectionBadge label={t("sensemaking.influenced_cards")} count={inf.influenced_cards.length} />
      <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
        {inf.influenced_cards.map((cid, i) => (
          <button
            key={cid}
            onClick={() => onCardClick(cid)}
            style={{
              background: "none", border: "none", color: "#64748b",
              cursor: "pointer", textAlign: "left", padding: "0.3rem 0.5rem",
              textDecoration: "underline", textUnderlineOffset: "2px", fontSize: "0.85rem",
            }}
          >
            {inf.influenced_card_titles[i] || cid}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── Card Evolution ────────────────────────────── */

function CardEvolutionView({
  analysis, t, onCardClick,
}: { analysis: SensemakingResponse; t: (k: string) => string; onCardClick: (id: string) => void }) {
  const evo = analysis.card_evolution;
  if (!evo) return <EmptyState icon="🌱" message={t("sensemaking.no_evolution")} />;
  return (
    <div>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
        {t("sensemaking.card_evolution")}
      </h2>
      <div style={{
        border: "1px solid var(--border, #e2e8f0)", borderRadius: "8px",
        padding: "1rem", background: "var(--bg-secondary, #fff)", marginBottom: "0.75rem",
      }}>
        <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>{t("sensemaking.source")}: {evo.source_label}</div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted, #94a3b8)" }}>
          {t("sensemaking.steps")}: {evo.step_count}
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {evo.steps.map((step, i) => (
          <div
            key={step.card_id}
            style={{
              border: "1px solid var(--border, #e2e8f0)", borderRadius: "8px",
              padding: "0.75rem 1rem", background: "var(--bg-secondary, #fff)",
              position: "relative",
            }}
          >
            <div style={{
              position: "absolute", top: "-0.5rem", left: "0.75rem",
              background: "var(--accent, #6366f1)", color: "#fff",
              borderRadius: "10px", padding: "0.1rem 0.4rem", fontSize: "0.65rem", fontWeight: 600,
            }}>
              Step {i + 1}
            </div>
            <button
              onClick={() => onCardClick(step.card_id)}
              style={{
                background: "none", border: "none", color: "var(--accent, #6366f1)",
                cursor: "pointer", fontWeight: 600, fontSize: "0.9rem", padding: 0,
                textDecoration: "underline", textUnderlineOffset: "2px", marginTop: "0.25rem",
              }}
            >
              {step.card_title}
            </button>
            <div style={{ marginTop: "0.35rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {step.tags.map((tg) => (
                <span key={tg} style={{
                  background: "#fef3c7", color: "#92400e", borderRadius: "4px",
                  padding: "0.1rem 0.4rem", fontSize: "0.7rem",
                }}>
                  #{tg}
                </span>
              ))}
              {step.wiki_sections.map((sec) => (
                <span key={sec} style={{
                  background: "#ede9fe", color: "#5b21b6", borderRadius: "4px",
                  padding: "0.1rem 0.4rem", fontSize: "0.7rem",
                }}>
                  §{sec}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Community Subgraphs ───────────────────────── */

function CommunitySubgraphsView({
  analysis, t, onCardClick,
}: { analysis: SensemakingResponse; t: (k: string) => string; onCardClick: (id: string) => void }) {
  const subs = analysis.community_subgraphs;
  if (subs.length === 0) {
    return <EmptyState icon="👥" message={t("sensemaking.no_community")} />;
  }
  return (
    <div>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
        {t("sensemaking.community_subgraphs")} ({subs.length})
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {subs.map((sg, idx) => (
          <div
            key={idx}
            style={{
              border: "1px solid var(--border, #e2e8f0)", borderRadius: "8px",
              padding: "1rem", background: "var(--bg-secondary, #fff)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <div>
                <span style={{
                  fontSize: "0.65rem", fontWeight: 600, textTransform: "uppercase",
                  color: "var(--accent, #6366f1)", marginRight: "0.5rem",
                }}>
                  {sg.community_type}
                </span>
                <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>{sg.community_label}</span>
              </div>
              <div style={{ display: "flex", gap: "0.75rem", fontSize: "0.7rem", color: "var(--text-muted, #94a3b8)" }}>
                <span>{sg.member_count} {t("sensemaking.member_count")}</span>
                <span>{sg.internal_edge_count} {t("sensemaking.internal_edges")}</span>
              </div>
            </div>

            {/* Member cards */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
              {sg.member_card_ids.map((cid, i) => (
                <button
                  key={cid}
                  onClick={() => onCardClick(cid)}
                  style={{
                    background: sg.bridge_card_ids.includes(cid) ? "#fef3c7" : "var(--bg-tertiary, #f8fafc)",
                    border: sg.bridge_card_ids.includes(cid) ? "1px solid #f59e0b" : "1px solid var(--border, #e2e8f0)",
                    borderRadius: "6px", padding: "0.25rem 0.5rem", cursor: "pointer",
                    fontSize: "0.75rem", color: "var(--text-primary, #1e293b)",
                  }}
                  title={sg.member_card_titles[i] || cid}
                >
                  {sg.bridge_card_ids.includes(cid) && <span style={{ marginRight: "0.2rem" }}>🌉</span>}
                  {(sg.member_card_titles[i] || cid).slice(0, 40)}
                  {(sg.member_card_titles[i] || cid).length > 40 ? "..." : ""}
                </button>
              ))}
            </div>

            {sg.bridge_card_ids.length > 0 && (
              <div style={{ marginTop: "0.5rem", fontSize: "0.7rem", color: "#92400e" }}>
                🌉 {sg.bridge_card_ids.length} {t("sensemaking.bridge_cards")}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Shared Components ─────────────────────────── */

function EmptyState({ icon, message }: { icon: string; message: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-center text-sm text-muted">
      <div className="mb-2 text-4xl">{icon}</div>
      <p>{message}</p>
    </div>
  );
}

function SectionBadge({ label, count }: { label: string; count: number }) {
  return (
    <div className="mb-1 mt-3 text-xs font-semibold" style={{ color: "var(--mf-text-secondary)" }}>
      {label} ({count})
    </div>
  );
}
