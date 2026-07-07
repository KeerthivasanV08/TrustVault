import { ReactNode } from "react";

export function Panel({
  title, subtitle, children, action, className = "", dense = false,
}: {
  title?: ReactNode; subtitle?: ReactNode; action?: ReactNode;
  children: ReactNode; className?: string; dense?: boolean;
}) {
  return (
    <section className={`glass-panel rounded-lg overflow-hidden flex flex-col ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between px-3 py-2 border-b border-border">
          <div className="min-w-0">
            {title && <div className="text-[11px] uppercase tracking-[0.18em] font-medium truncate">{title}</div>}
            {subtitle && <div className="text-[10px] text-muted-foreground mt-0.5">{subtitle}</div>}
          </div>
          {action}
        </header>
      )}
      <div className={`flex-1 min-h-0 ${dense ? "" : "p-3"}`}>{children}</div>
    </section>
  );
}

export function StatCard({
  label, value, sub, tone = "default", icon, trend,
}: {
  label: string; value: ReactNode; sub?: ReactNode;
  tone?: "default" | "critical" | "warning" | "success" | "primary";
  icon?: ReactNode; trend?: { dir: "up" | "down"; value: string };
}) {
  const toneCls = {
    default: "border-border",
    critical: "border-critical/40 glow-red",
    warning: "border-warning/40",
    success: "border-success/40",
    primary: "border-primary/40 glow-blue",
  }[tone];
  const valTone = {
    default: "text-foreground",
    critical: "text-critical",
    warning: "text-warning",
    success: "text-success",
    primary: "text-primary",
  }[tone];
  return (
    <div className={`relative overflow-hidden rounded-lg bg-card/60 border ${toneCls} p-3`}>
      <div className="absolute inset-0 grid-bg opacity-[0.05]" />
      <div className="relative">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-[10px] uppercase tracking-[0.18em]">{label}</span>
          {icon}
        </div>
        <div className={`mt-1 text-2xl font-semibold mono ${valTone}`}>{value}</div>
        <div className="mt-1 flex items-center gap-2 text-[11px] text-muted-foreground">
          {sub}
          {trend && (
            <span className={`mono ${trend.dir === "up" ? "text-success" : "text-critical"}`}>
              {trend.dir === "up" ? "▲" : "▼"} {trend.value}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
