import type { HomeStatusResponse, WorkflowSummaryResponse } from "../api/types";
import { NextActionCard } from "../components/NextActionCard";
import { StatusCard } from "../components/StatusCard";

export function HomePage({ data, workflow, onNavigate }: { data: HomeStatusResponse; workflow?: WorkflowSummaryResponse; onNavigate: (href: string) => void }) {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">首页</h1>
        <p className="mt-1 text-sm text-muted">选择本地知识工作台的下一步操作。</p>
      </header>
      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard label="审阅 AI 草稿" value={data.safety.pending_drafts_count} status={data.safety.pending_drafts_count > 0 ? "warn" : "ok"} detail="待审阅的 AI 生成知识草稿。" href="/drafts" onNavigate={onNavigate} />
        <StatusCard label="管理知识源" value={workflow?.inbox_pending_count ?? "-"} status={(workflow?.inbox_pending_count ?? 0) > 0 ? "warn" : "ok"} detail="添加原始资料并查看处理状态。" href="/sources" onNavigate={onNavigate} />
        <StatusCard label="浏览知识库" value={data.vault.approved_card_count} status={data.vault.approved_card_count > 0 ? "ok" : "info"} detail="已确认的知识卡片，可供阅读、编辑和搜索。" href="/library" onNavigate={onNavigate} />
      </div>
      <section className="grid gap-4 md:grid-cols-2">
        <StatusCard label="搜索知识" value={data.recall.index_exists ? "就绪" : "需建索引"} status={data.recall.index_exists ? "ok" : "warn"} detail="仅搜索已确认的知识卡片。" nextAction={data.recall.next_action} href="/recall" onNavigate={onNavigate} />
        <StatusCard label="检查配置" value={data.provider.model_setup === "ready" ? "就绪" : "待检查"} status={data.provider.model_setup === "ready" ? "ok" : "warn"} detail="检查本地知识库和模型配置。" href="/setup" onNavigate={onNavigate} />
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-ink">下一步操作</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {data.next_actions.map((action) => (
            <NextActionCard action={action} key={action.label} onNavigate={onNavigate} />
          ))}
        </div>
      </section>
    </div>
  );
}
