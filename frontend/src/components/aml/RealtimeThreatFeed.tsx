import { AlertTriangle, Clock, Network, UserCheck, Zap } from "lucide-react";
import { useStore } from "@/store/realtime";

const iconFor = (lvl: string) => {
  if (lvl === "critical") return AlertTriangle;
  if (lvl === "warning") return Clock;
  if (lvl === "success") return UserCheck;
  return Zap;
};
const toneFor = (lvl: string) => {
  if (lvl === "critical") return "text-critical border-critical/30 bg-critical/5";
  if (lvl === "warning") return "text-warning border-warning/30 bg-warning/5";
  if (lvl === "success") return "text-success border-success/30 bg-success/5";
  return "text-info border-info/30 bg-info/5";
};

export function RealtimeThreatFeed({ compact = false }: { compact?: boolean }) {
  const ticker = useStore((s) => s.ticker);
  const connected = useStore((s) => s.connected);
  const connectionStatus = useStore((s) => s.connectionStatus);
  const hasEvents = ticker.length > 0;
  return (
    <div className="glass-panel rounded-lg overflow-hidden flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <Network className="h-3.5 w-3.5 text-primary" />
          <span className="text-[11px] uppercase tracking-[0.18em] font-medium">Live Threat Feed</span>
        </div>
        <span className="text-[10px] mono text-muted-foreground flex items-center gap-1">
          <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-success pulse-dot text-success" : "bg-critical text-critical"}`} />
          {connected ? "STREAMING" : connectionStatus === "reconnecting" ? "RECONNECTING" : "DISCONNECTED"}
        </span>
      </div>
      <div className={`flex-1 overflow-y-auto scrollbar-thin divide-y divide-border/50`}>
        {hasEvents ? ticker.slice(0, compact ? 8 : 30).map((t, i) => {
          const Icon = iconFor(t.level);
          return (
            <div key={t.ts + "-" + i} className={`px-3 py-2 text-xs flex items-start gap-2 ${i === 0 ? "row-enter" : ""}`}>
              <span className={`mt-0.5 h-5 w-5 rounded shrink-0 flex items-center justify-center border ${toneFor(t.level)}`}>
                <Icon className="h-3 w-3" />
              </span>
              <div className="flex-1 min-w-0">
                <div className="truncate">{t.text}</div>
                <div className="text-[10px] text-muted-foreground mono mt-0.5">{new Date(t.ts).toLocaleTimeString()}</div>
              </div>
            </div>
          );
        }) : connected ? (
          <div className="px-3 py-4 text-xs text-muted-foreground">Waiting for realtime alert stream...</div>
        ) : (
          <div className="px-3 py-4 text-xs text-muted-foreground">Realtime alert stream disconnected</div>
        )}
      </div>
    </div>
  );
}
