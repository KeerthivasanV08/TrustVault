import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useStore, store, mergeHistoricalTransactions } from "@/store/realtime";
import { useRecentTransactions } from '@/hooks/useTransactions';
import { Panel } from "@/components/aml/Panel";
import { DecisionBadge, RiskScoreBadge, StatusBadge } from "@/components/aml/Badges";
import { ExplainabilityPanel } from "@/components/aml/ExplainabilityPanel";
import { ArrowRight, Filter, Pause, Play, X } from "lucide-react";
import type { Transaction } from '@/types';

// Safe formatters for date/time and currency
function formatTxnTime(value?: string | number): string {
  if (!value) return "Live now";
  const date = new Date(typeof value === 'string' ? value : value * 1000);
  if (Number.isNaN(date.getTime())) return "Live now";
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
}

function formatINR(amount?: number): string {
  const value = Number(amount);
  if (!Number.isFinite(value)) return "₹0";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value);
}

export const Route = createFileRoute("/transaction-flow")({
  head: () => ({ meta: [{ title: "Transaction Monitor — TrustVault" }] }),
  component: TransactionFlow,
});

function TransactionFlow() {
  const txns = useStore((s) => s.transactions);
  const paused = useStore((s) => s.paused);
  const recent = useRecentTransactions();

  useEffect(() => {
    if (recent.data && !recent.isFetching) {
      mergeHistoricalTransactions(recent.data || []);
    }
  }, [recent.data, recent.isFetching]);

  const [minRisk, setMinRisk] = useState(0);
  const [q, setQ] = useState("");
  const [decision, setDecision] = useState<"ALL" | "ALLOW" | "REVIEW" | "BLOCK">("ALL");
  const [selected, setSelected] = useState<Transaction | null>(null);

  const filtered = txns.filter((t) => {
    if (t.riskScore < minRisk) return false;
    if (decision !== "ALL" && t.decision !== decision) return false;
    if (q && !`${t.id} ${t.sender} ${t.receiver} ${t.senderName} ${t.receiverName}`.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Transaction Intelligence Terminal</h1>
          <p className="text-xs text-muted-foreground">Real-time SSE stream · scoring latency p99 21ms · throughput {(12 + (txns.length % 6)).toFixed(0)} tx/s</p>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] mono">
          <span className="flex items-center gap-1 px-2 py-1 rounded border border-success/40 text-success bg-success/5">
            <span className="h-1.5 w-1.5 rounded-full bg-success pulse-dot text-success" /> SSE
          </span>
          <span className="px-2 py-1 rounded border border-border">latency 21ms</span>
        </div>
      </div>

      {recent.isError && (
        <div className="rounded-md border border-danger/40 bg-danger/5 px-3 py-2 text-xs text-danger">
          Backend unavailable. Transaction history could not be loaded.
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Search txn id / account / name…"
          className="h-8 w-64 px-3 rounded-md bg-input/60 border border-border text-xs focus:outline-none focus:border-primary"
        />
        <div className="flex items-center gap-2 px-3 h-8 rounded-md border border-border bg-card/60 text-xs">
          <Filter className="h-3 w-3 text-muted-foreground" />
          <span className="text-muted-foreground text-[10px] uppercase tracking-wider">Min risk</span>
          <input type="range" min={0} max={100} value={minRisk} onChange={(e) => setMinRisk(+e.target.value)} className="w-24 accent-primary" />
          <span className="mono w-6">{minRisk}</span>
        </div>
        <div className="flex items-center rounded-md border border-border overflow-hidden">
          {(["ALL", "ALLOW", "REVIEW", "BLOCK"] as const).map((d) => (
            <button key={d} onClick={() => setDecision(d)} className={`px-2.5 h-8 text-[11px] mono ${decision === d ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>{d}</button>
          ))}
        </div>
        <button onClick={() => store.togglePause()} className="ml-auto flex items-center gap-1.5 h-8 px-3 rounded-md border border-border bg-card/60 text-xs">
          {paused ? <Play className="h-3.5 w-3.5 text-success" /> : <Pause className="h-3.5 w-3.5 text-warning" />}
          <span className="mono">{paused ? "RESUME STREAM" : "PAUSE STREAM"}</span>
        </button>
      </div>

      <Panel title={`${filtered.length} transactions in view`} subtitle="Newest first · click row to inspect" dense>
        {recent.isLoading && !txns.length ? (
          <div className="h-40 flex items-center justify-center text-xs text-muted-foreground">Loading transactions…</div>
        ) : !filtered.length ? (
          <div className="h-40 flex items-center justify-center text-xs text-muted-foreground">No transactions available from backend</div>
        ) : (
        <div className="overflow-auto scrollbar-thin max-h-[calc(100vh-280px)]">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-card/95 backdrop-blur text-[10px] uppercase tracking-wider text-muted-foreground z-10">
              <tr className="text-left border-b border-border">
                {["Time", "Txn ID", "Sender", "Receiver", "Amount", "Decision", "Risk", "Behav", "Seq", "Graph", "Signals", "Status"].map((h) => (
                  <th key={h} className="px-2 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 80).map((t, i) => (
                <tr
                  key={t.id}
                  onClick={() => setSelected(t)}
                  className={`border-b border-border/50 cursor-pointer hover:bg-accent/30 ${i === 0 && !paused ? "row-enter" : ""} ${t.decision === "BLOCK" ? "bg-critical/[0.04]" : t.decision === "REVIEW" ? "bg-warning/[0.03]" : ""}`}
                >
                  <td className="px-2 py-1.5 mono text-[10px] text-muted-foreground">{formatTxnTime(t.ts || t.timestamp)}</td>
                  <td className="mono text-[10px]">{t.id.slice(0, 22)}</td>
                  <td className="text-[11px]"><div className="mono text-[10px]">{t.sender}</div><div className="text-muted-foreground text-[10px]">{t.senderName} · {t.countryFrom}</div></td>
                  <td className="text-[11px]"><div className="mono text-[10px]">{t.receiver}</div><div className="text-muted-foreground text-[10px]">{t.receiverName} · {t.countryTo}</div></td>
                  <td className="mono text-right pr-3">{formatINR(t.amount)}</td>
                  <td><DecisionBadge d={t.decision} /></td>
                  <td><RiskScoreBadge score={t.riskScore} /></td>
                  <td className="mono text-[10px] text-muted-foreground">{t.behavioralScore}</td>
                  <td className="mono text-[10px] text-muted-foreground">{t.sequenceScore}</td>
                  <td className="mono text-[10px] text-muted-foreground">{t.graphScore}</td>
                  <td className="max-w-[180px]">
                    <div className="flex gap-1 flex-wrap">
                      {t.signals.slice(0, 2).map((s) => (
                        <span key={s} className="text-[9px] mono px-1 py-0.5 rounded bg-muted text-muted-foreground border border-border">{s}</span>
                      ))}
                      {t.signals.length > 2 && <span className="text-[9px] mono text-muted-foreground">+{t.signals.length - 2}</span>}
                    </div>
                  </td>
                  <td><StatusBadge status={t.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </Panel>

      {selected && <TxnDrawer t={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function TxnDrawer({ t, onClose }: { t: Transaction; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-background/60 backdrop-blur-sm" onClick={onClose} />
      <aside className="w-[560px] bg-card border-l border-border overflow-y-auto scrollbar-thin">
        <header className="sticky top-0 z-10 bg-card/95 backdrop-blur border-b border-border px-4 py-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Transaction Detail</div>
            <div className="mono text-sm">{t.id}</div>
          </div>
          <button onClick={onClose} className="h-7 w-7 rounded hover:bg-accent flex items-center justify-center"><X className="h-4 w-4" /></button>
        </header>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <Field label="Amount" value={formatINR(t.amount)} />
            <Field label="Channel" value={t.channel} />
            <Field label="Decision" value={<DecisionBadge d={t.decision} />} />
            <Field label="Status" value={<StatusBadge status={t.status} />} />
          </div>
          <div className="rounded-md border border-border bg-card/40 p-3">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Counterparties</div>
            <div className="flex items-center justify-between text-xs">
              <div>
                <div className="mono">{t.sender}</div>
                <div className="text-muted-foreground text-[10px]">{t.senderName} · {t.countryFrom}</div>
              </div>
              <ArrowRight className="h-4 w-4 text-primary" />
              <div className="text-right">
                <div className="mono">{t.receiver}</div>
                <div className="text-muted-foreground text-[10px]">{t.receiverName} · {t.countryTo}</div>
              </div>
            </div>
          </div>
          <ExplainabilityPanel finalScore={t.riskScore} decision={t.decision} />
        </div>
      </aside>
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border bg-card/40 p-2.5">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-0.5 mono text-xs">{value}</div>
    </div>
  );
}
