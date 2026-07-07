import { Bell, Search, Wifi, WifiOff, Pause, Play, ShieldCheck } from "lucide-react";
import { useStore, store } from "@/store/realtime";
import { useEffect, useState } from "react";
import { fetchSystemHealth } from "@/services/api";

type RuntimeHealth = {
  backend: string;
  behavioral_model: string;
  sequence_model: string;
  neo4j_graph_engine: string;
  runtime_mode: string;
  transaction_sse: string;
  alert_sse: string;
};

function Pill({ label, value, tone = "default" }: { label: string; value: string | number; tone?: "default" | "critical" | "warning" | "success" }) {
  const toneCls = {
    default: "text-foreground",
    critical: "text-critical",
    warning: "text-warning",
    success: "text-success",
  }[tone];
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-border bg-card/60">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className={`text-sm font-semibold mono ${toneCls}`}>{value}</span>
    </div>
  );
}

export function Header() {
  const connected = useStore((s) => s.connected);
  const paused = useStore((s) => s.paused);
  const m = useStore((s) => s.metrics);
  const tickerLen = useStore((s) => s.ticker.length);
  const [runtimeHealth, setRuntimeHealth] = useState<RuntimeHealth | null>(null);
  const [time, setTime] = useState<Date | null>(null);
  useEffect(() => {
    setTime(new Date());
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const health = await fetchSystemHealth();
        if (!active) return;
        setRuntimeHealth({
          backend: health.readiness?.status === 'READY' ? 'healthy' : 'degraded',
          behavioral_model: health.modelHealth?.behavioral_model ?? 'failed',
          sequence_model: health.modelHealth?.sequence_model ?? 'failed',
          neo4j_graph_engine: health.modelHealth?.graph_engine ?? 'failed',
          runtime_mode: health.modelHealth?.runtime_mode ?? 'DEGRADED',
          transaction_sse: 'active',
          alert_sse: 'active',
        });
      } catch {
        if (active) {
          setRuntimeHealth(null);
        }
      }
    };

    void load();
    const id = setInterval(() => { void load(); }, 30000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const runtimeMode = runtimeHealth?.runtime_mode ?? 'DEGRADED';
  const runtimeTone = runtimeMode === 'FULL' ? 'border-success/40 text-success' : runtimeMode === 'DEGRADED' ? 'border-warning/40 text-warning' : 'border-critical/40 text-critical';

  return (
    <header className="h-14 shrink-0 border-b border-border bg-background/70 backdrop-blur-md flex items-center px-4 gap-3 sticky top-0 z-30">
      <div className="flex items-center gap-2 mr-2">
        <ShieldCheck className="h-4 w-4 text-primary" />
        <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">SOC / AML-OPS</span>
      </div>

      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <input
          placeholder="Search accounts, transactions, alerts, cases…"
          className="w-full h-8 pl-8 pr-3 rounded-md bg-input/60 border border-border text-xs placeholder:text-muted-foreground focus:outline-none focus:border-primary"
        />
        <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] mono px-1 py-0.5 rounded border border-border text-muted-foreground">⌘K</span>
      </div>

      <Pill label="Txn/s" value={(12 + (tickerLen % 8)).toFixed(0)} />
      <Pill label="P1" value={m.p1} tone="critical" />
      <Pill label="Review" value={m.reviewQueue} tone="warning" />
      <Pill label="Cases" value={m.activeCases} />

      <div className={`hidden xl:flex items-center gap-2 px-2.5 h-8 rounded-md border bg-card/60 ${runtimeTone}`} title={runtimeHealth ? `backend:${runtimeHealth.backend} behavioral:${runtimeHealth.behavioral_model} sequence:${runtimeHealth.sequence_model} neo4j:${runtimeHealth.neo4j_graph_engine} tx:${runtimeHealth.transaction_sse} alert:${runtimeHealth.alert_sse}` : 'Checking AML runtime health'}>
        <div className={`h-2 w-2 rounded-full ${runtimeMode === 'FULL' ? 'bg-success' : runtimeMode === 'DEGRADED' ? 'bg-warning' : 'bg-critical'}`} />
        <div className="leading-tight">
          <div className="text-[9px] uppercase tracking-wider text-muted-foreground">Runtime</div>
          <div className="text-[10px] mono font-semibold">{runtimeMode}</div>
        </div>
        <div className="hidden 2xl:flex items-center gap-1.5 text-[9px] mono text-muted-foreground border-l border-border pl-2 ml-1">
          <span>B:{runtimeHealth?.backend ?? '...'}</span>
          <span>M:{runtimeHealth?.behavioral_model ?? '...'}</span>
          <span>S:{runtimeHealth?.sequence_model ?? '...'}</span>
          <span>G:{runtimeHealth?.neo4j_graph_engine ?? '...'}</span>
          <span>TX:{runtimeHealth?.transaction_sse ?? '...'}</span>
          <span>AL:{runtimeHealth?.alert_sse ?? '...'}</span>
        </div>
      </div>

      <button
        onClick={() => store.togglePause()}
        className="h-8 px-2.5 rounded-md border border-border bg-card/60 hover:bg-card text-xs flex items-center gap-1.5"
      >
        {paused ? <Play className="h-3.5 w-3.5 text-success" /> : <Pause className="h-3.5 w-3.5 text-warning" />}
        <span className="mono">{paused ? "RESUME" : "PAUSE"}</span>
      </button>

      <div className={`flex items-center gap-1.5 px-2.5 h-8 rounded-md border ${connected ? "border-success/40 text-success" : "border-critical/40 text-critical"} bg-card/60`}>
        {connected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
        <span className="text-[10px] uppercase tracking-wider mono">{connected ? "SSE LIVE" : "RECONNECTING"}</span>
        <span className={`h-1.5 w-1.5 rounded-full pulse-dot ${connected ? "bg-success text-success" : "bg-critical text-critical"}`} />
      </div>

      <button className="relative h-8 w-8 rounded-md border border-border bg-card/60 hover:bg-card flex items-center justify-center">
        <Bell className="h-4 w-4" />
        <span className="absolute -top-1 -right-1 h-4 min-w-4 px-1 text-[10px] mono rounded-full bg-critical text-critical-foreground flex items-center justify-center">{m.p1}</span>
      </button>

      <div className="flex items-center gap-2 pl-3 border-l border-border">
        <div className="h-7 w-7 rounded-full bg-gradient-to-br from-primary to-info flex items-center justify-center text-[11px] font-bold text-primary-foreground">AK</div>
        <div className="leading-tight">
          <div className="text-xs font-medium">A. Khan</div>
          <div className="text-[10px] text-muted-foreground mono">{time ? `${time.toISOString().slice(11, 19)}Z` : "—"}</div>
        </div>
      </div>
    </header>
  );
}
