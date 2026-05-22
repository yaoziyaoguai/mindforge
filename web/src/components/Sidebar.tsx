import { BookOpen, BookMarked, CheckSquare, Home, Inbox, Library, Search, Settings, Trash2 } from "lucide-react";
import { cx } from "../lib/utils";

const items = [
  { href: "/", label: "首页", icon: Home },
  { href: "/setup", label: "连接模型", icon: Settings },
  { href: "/sources", label: "知识源", icon: Inbox },
  { href: "/drafts", label: "审阅草稿", icon: CheckSquare },
  { href: "/library", label: "知识库", icon: Library },
  { href: "/wiki", label: "Wiki", icon: BookMarked },
  { href: "/recall", label: "搜索", icon: Search },
  { href: "/trash", label: "回收站", icon: Trash2 },
];

export function Sidebar({ path, onNavigate }: { path: string; onNavigate: (href: string) => void }) {
  return (
    <nav className="w-64 shrink-0 border-r border-line bg-[#efebe3] px-3 py-4" aria-label="Main navigation">
      <div className="mb-6 flex items-center gap-2 px-2 text-lg font-semibold text-ink">
        <BookOpen className="h-5 w-5" aria-hidden="true" />
        MindForge
      </div>
      <div className="space-y-1">
        {items.map((item) => {
          const active = path === item.href || (item.href !== "/" && path.startsWith(item.href));
          const Icon = item.icon;
          return (
            <button
              key={item.href}
              type="button"
              onClick={() => onNavigate(item.href)}
              className={cx(
                "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm",
                active ? "bg-panel text-ink shadow-subtle" : "text-muted hover:bg-white/60 hover:text-ink",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
