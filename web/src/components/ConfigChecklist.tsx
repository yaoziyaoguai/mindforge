import { statusTone } from "../lib/utils";
import type { StatusItem } from "../api/types";

export function ConfigChecklist({ items }: { items: StatusItem[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-ink">Setup checks</h2>
      <div className="divide-y divide-line rounded-md border border-line bg-panel">
        {items.map((item) => (
          <details key={item.key} className="group p-4">
            <summary className="flex cursor-pointer list-none items-start justify-between gap-4">
              <span>
                <span className="font-medium text-ink">{item.label}</span>
                <span className="mt-1 block text-sm text-muted">{item.detail ?? item.value}</span>
              </span>
              <span className={`rounded-full border px-2 py-0.5 text-xs ${statusTone(item.status)}`}>{item.value}</span>
            </summary>
            <div className="mt-3 rounded-md bg-stone-50 p-3 text-sm text-muted">
              <p>{explainItem(item)}</p>
              {item.next_action ? (
                <p className="mt-2 text-primary">{item.next_action.command ?? item.next_action.description}</p>
              ) : null}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}

function explainItem(item: StatusItem): string {
  // 中文学习型说明：这个组件只保留用户能理解的设置检查，不再展示开发/测试
  // 兼容层字段。真实模型和本地 secret store 才是普通用户主路径。
  if (item.key === "provider") return "Model setup is shown without exposing API key values. Keys are configured, missing, or hidden.";
  if (item.key === "vault") return "Vault writes require explicit local actions such as saving a card body or approving a draft.";
  if (item.key === "config") return "MindForge loaded local setup for this workspace. Web never prints secret values.";
  return item.detail ?? item.value;
}
