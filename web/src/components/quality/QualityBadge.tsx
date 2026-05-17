/** M1 QualityBadge — SDD §7 rule 26 */

interface QualityBadgeProps {
  level: "high" | "medium" | "low";
  score: number;
  className?: string;
}

const STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  high: { bg: "bg-green-50 border-green-200", text: "text-green-700", dot: "bg-green-500" },
  medium: { bg: "bg-amber-50 border-amber-200", text: "text-amber-700", dot: "bg-amber-500" },
  low: { bg: "bg-red-50 border-red-200", text: "text-red-700", dot: "bg-red-500" },
};

const LABELS: Record<string, string> = {
  high: "高质量",
  medium: "中质量",
  low: "低质量",
};

export function QualityBadge({ level, score, className = "" }: QualityBadgeProps) {
  const s = STYLES[level] ?? STYLES.medium;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${s.bg} ${s.text} ${className}`}
      title={`质量评分：${score} 分`}
    >
      <span className={`w-2 h-2 rounded-full ${s.dot}`} />
      {LABELS[level] ?? level}
      <span className="opacity-60">{score}</span>
    </span>
  );
}
