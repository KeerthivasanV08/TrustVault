import type { Priority } from '@/types';

export function PriorityBadge({ p }: { p: Priority }) {
  const cls = p === "P1"
    ? "bg-critical/15 text-critical border-critical/40 pulse-critical"
    : p === "P2"
    ? "bg-warning/15 text-warning border-warning/40"
    : "bg-muted text-muted-foreground border-border";
  return (
    <span className={`inline-flex items-center px-1.5 h-5 rounded text-[10px] font-bold mono border ${cls}`}>
      {p}
    </span>
  );
}

export function RiskScoreBadge({ score }: { score: number }) {
  const tone = score > 85 ? "critical" : score > 65 ? "warning" : score > 40 ? "info" : "success";
  const cls = {
    critical: "text-critical bg-critical/10 border-critical/40",
    warning: "text-warning bg-warning/10 border-warning/40",
    info: "text-info bg-info/10 border-info/40",
    success: "text-success bg-success/10 border-success/40",
  }[tone];
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 h-5 rounded text-[10px] mono border ${cls}`}>
      <span className="font-bold">{score}</span>
      <span className="opacity-60">/100</span>
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const t: Record<string, string> = {
    OPEN: "bg-info/10 text-info border-info/30",
    ACK: "bg-muted text-muted-foreground border-border",
    ESCALATED: "bg-warning/10 text-warning border-warning/40",
    CLOSED: "bg-success/10 text-success border-success/30",
    SAR_FILED: "bg-primary/10 text-primary border-primary/40",
    BLOCKED: "bg-critical/10 text-critical border-critical/40",
    HELD: "bg-warning/10 text-warning border-warning/40",
    SETTLED: "bg-success/10 text-success border-success/30",
    PENDING: "bg-muted text-muted-foreground border-border",
    IN_REVIEW: "bg-info/10 text-info border-info/30",
  };
  return (
    <span className={`inline-flex items-center px-1.5 h-5 rounded text-[10px] mono border ${t[status] ?? t.OPEN}`}>
      {status}
    </span>
  );
}

export function DecisionBadge({ d }: { d: "ALLOW" | "REVIEW" | "BLOCK" }) {
  const cls = d === "BLOCK"
    ? "bg-critical/15 text-critical border-critical/40"
    : d === "REVIEW"
    ? "bg-warning/15 text-warning border-warning/40"
    : "bg-success/15 text-success border-success/30";
  return (
    <span className={`inline-flex items-center px-1.5 h-5 rounded text-[10px] font-semibold mono border ${cls}`}>
      {d}
    </span>
  );
}
