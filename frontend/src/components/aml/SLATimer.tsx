import { useEffect, useState } from "react";

export function SLATimer({ dueAt }: { dueAt?: number }) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  if (dueAt == null || now == null) {
    return <span className={`mono text-[11px] px-1.5 py-0.5 rounded border bg-muted/40 text-muted-foreground border-border`}>—</span>;
  }

  const ms = dueAt - now;
  const breached = ms <= 0;
  const sec = Math.abs(Math.floor(ms / 1000));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const fmt = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  const urgent = !breached && ms < 5 * 60_000;

  return (
    <span
      className={`mono text-[11px] px-1.5 py-0.5 rounded border ${
        breached
          ? "bg-critical/15 text-critical border-critical/50 pulse-critical"
          : urgent
          ? "bg-warning/15 text-warning border-warning/40"
          : "bg-muted/40 text-muted-foreground border-border"
      }`}
    >
      {breached ? `+${fmt}` : fmt}
    </span>
  );
}
