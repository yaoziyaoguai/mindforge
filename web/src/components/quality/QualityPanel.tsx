/** M1 QualityPanel — SDD §7 rules 26-28, RFC §7 FR1.6。

在 card detail 中显示 quality metadata：
- quality badge 始终可见
- rubric breakdown 可展开
*/

import { useState, useEffect } from "react";
import type { CardQuality } from "../../api/quality";
import { fetchCardQuality } from "../../api/quality";
import { QualityBadge } from "./QualityBadge";
import { QualityWarnings } from "./QualityWarnings";

interface QualityPanelProps {
  cardId: string;
}

export function QualityPanel({ cardId }: QualityPanelProps) {
  const [quality, setQuality] = useState<CardQuality | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchCardQuality(cardId)
      .then((q) => { if (!cancelled) setQuality(q); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "获取质量数据失败"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [cardId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-400 py-1">
        <span className="inline-block w-3 h-3 border-2 border-gray-300 border-t-transparent rounded-full animate-spin" />
        正在分析卡片质量...
      </div>
    );
  }

  if (error || !quality) {
    return (
      <div className="text-xs text-gray-400 py-1">
        {error ? `质量分析不可用：${error}` : "暂无质量数据"}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* 始终可见的质量 badge + 类型标签 */}
      <div className="flex items-center gap-2 flex-wrap">
        <QualityBadge level={quality.overall_level} score={quality.overall_score} />
        {quality.card_type && (
          <span className="inline-flex px-2 py-0.5 rounded text-xs bg-blue-50 text-blue-600 border border-blue-100">
            {quality.card_type}
          </span>
        )}
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-gray-400 hover:text-gray-600 underline underline-offset-2"
        >
          {expanded ? "收起详情" : "查看详情"}
        </button>
      </div>

      {/* 可展开的 rubric details */}
      {expanded && (
        <div className="space-y-3 pl-1 border-l-2 border-gray-100">
          {/* Rubric 维度分 */}
          <div className="space-y-1">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              质量维度
            </h4>
            <div className="grid grid-cols-1 gap-1">
              {quality.rubric_scores.map((rs) => (
                <div key={rs.dimension} className="flex items-center gap-2 text-xs">
                  <span className="w-24 text-gray-500 shrink-0">{rs.dimension}</span>
                  <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${(rs.score / rs.max_score) * 100}%`,
                        backgroundColor:
                          rs.score >= 0.7 ? "#22c55e" : rs.score >= 0.4 ? "#f59e0b" : "#ef4444",
                      }}
                    />
                  </div>
                  <span className="w-8 text-right text-gray-600 tabular-nums">
                    {Math.round(rs.score * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Warnings */}
          <QualityWarnings warnings={quality.warnings} />

          {/* 维护建议 */}
          {(quality.regenerate_suggestion || quality.split_candidate || quality.merge_candidate) && (
            <div className="space-y-1">
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                维护建议
              </h4>
              {quality.regenerate_suggestion && (
                <p className="text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded px-2 py-1">
                  {quality.regenerate_suggestion}
                </p>
              )}
              {quality.split_candidate && (
                <p className="text-xs text-blue-600 bg-blue-50 border border-blue-100 rounded px-2 py-1">
                  建议拆分为多张卡片（可能包含多个独立主题）
                </p>
              )}
              {quality.merge_candidate && (
                <p className="text-xs text-purple-600 bg-purple-50 border border-purple-100 rounded px-2 py-1">
                  建议与其他卡片合并（当前内容过短）
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
