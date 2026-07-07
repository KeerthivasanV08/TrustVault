import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo } from 'react';
import { useStore, mergeHistoricalTransactions, mergeHistoricalAlerts } from "@/store/realtime";
import { StatCard, Panel } from "@/components/aml/Panel";
import { DecisionBadge, PriorityBadge, RiskScoreBadge } from "@/components/aml/Badges";
import { useDashboardMetrics } from '@/hooks/useDashboard';
import { useRecentTransactions } from '@/hooks/useTransactions';
import { useAlerts } from '@/hooks/useAlerts';
import { useGraphSnapshot } from '@/hooks/useGraph';
import type { Transaction } from '@/types';
import {
  Activity, AlertTriangle, Ban, Briefcase, FileSignature, GitMerge,
  ShieldCheck, ShieldAlert, Users, ArrowRight,
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  buildRiskTrend,
  buildRiskDistribution,
  buildChannelComposition,
  buildHeatmap,
} from '@/lib/dashboardSelectors';

export const Route = createFileRoute("/")({
  head: () => ({ meta: [{ title: "Command Center — TrustVault AML" }] }),
  component: Dashboard,
});

const PIE_TOOLTIP_STYLE = {
  background: "#0f172a",
  color: "#f8fafc",
  border: "1px solid rgba(148, 163, 184, 0.28)",
  borderRadius: "10px",
  boxShadow: "0 14px 30px rgba(0, 0, 0, 0.45)",
  fontSize: 12,
  padding: "10px 12px",
};

function PieRiskTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const item = payload[0]?.payload;
  const name = item?.name ?? label ?? 'Risk';
  const value = item?.value ?? payload[0]?.value ?? 0;
  return (
    <div style={PIE_TOOLTIP_STYLE}>
      <div className="text-[10px] uppercase tracking-wider text-slate-400">Risk distribution</div>
      <div className="mt-1 font-semibold text-slate-50">{name}</div>
      <div className="mt-1 text-sm text-slate-200">{Number(value).toLocaleString()}</div>
    </div>
  );
}

function Dashboard() {
  const m = useStore((s) => s.metrics || {});
  const liveTxns = useStore((s) => s.transactions);
  const metricsQ = useDashboardMetrics();
  const txnsQ = useRecentTransactions();
  const alertsQ = useAlerts();
  const graphQ = useGraphSnapshot();

  useEffect(() => {
    if (txnsQ.data && !txnsQ.isFetching) mergeHistoricalTransactions(txnsQ.data);
  }, [txnsQ.data, txnsQ.isFetching]);

  useEffect(() => {
    if (alertsQ.data && !alertsQ.isFetching) mergeHistoricalAlerts(alertsQ.data);
  }, [alertsQ.data, alertsQ.isFetching]);

  const recentTransactions: Transaction[] = txnsQ.data ?? [];
  const liveTransactions: Transaction[] = liveTxns ?? [];

  const dashboardTransactions = useMemo(() => {
    const merged = new Map<string, Transaction>();
    for (const txn of [...liveTransactions, ...recentTransactions]) {
      const id = txn.transactionId || txn.transId || txn.trans_id || txn.id;
      if (id) merged.set(id, txn);
    }
    return Array.from(merged.values());
  }, [liveTransactions, recentTransactions]);

  const metrics = {
    totalTxn: metricsQ.data?.total_transactions ?? m.total_transactions ?? m.totalTxn ?? 0,
    blocked: metricsQ.data?.blocked_transactions ?? m.blocked_transactions ?? m.blocked ?? 0,
    reviewQueue: metricsQ.data?.review_queue ?? m.review_queue ?? m.reviewQueue ?? 0,
    p1: metricsQ.data?.high_risk_count ?? m.high_risk_count ?? m.p1 ?? 0,
    activeCases: metricsQ.data?.cases ?? m.cases ?? m.activeCases ?? 0,
    sar: metricsQ.data?.sar ?? m.sar ?? 0,
    mules: metricsQ.data?.mules ?? m.mules ?? 0,
    networkRisk: metricsQ.data?.escalations ?? m.escalations ?? m.networkRisk ?? 0,
  };

  const alerts = alertsQ.data ?? [];

  const riskTrendSeries = buildRiskTrend(dashboardTransactions, alerts);
  const riskDistribution = buildRiskDistribution(dashboardTransactions, alerts);
  const channelRiskData = buildChannelComposition(dashboardTransactions);
  const fraudHeatmap = buildHeatmap(dashboardTransactions);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Command Center</h1>
          <p className="text-xs text-muted-foreground">Real-time AML operations — global view</p>
        </div>
        <div className="flex items-center gap-2 text-[11px] mono text-muted-foreground">
          <span className="px-2 py-1 rounded border border-success/40 text-success bg-success/5">SOC-1 NOMINAL</span>
          <span className="px-2 py-1 rounded border border-warning/40 text-warning bg-warning/5">ELEVATED THREAT</span>
          <span className="px-2 py-1 rounded border border-border">Window: 24h</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3">
        <StatCard label="Total Txn (24h)" value={metrics.totalTxn.toLocaleString()} icon={<Activity className="h-3.5 w-3.5" />} trend={{ dir: "up", value: "4.2%" }} />
        <StatCard label="Blocked" value={metrics.blocked.toLocaleString()} tone="critical" icon={<Ban className="h-3.5 w-3.5" />} trend={{ dir: "up", value: "0.9%" }} />
        <StatCard label="Review Queue" value={metrics.reviewQueue} tone="warning" icon={<ShieldAlert className="h-3.5 w-3.5" />} />
        <StatCard label="P1 Alerts" value={metrics.p1} tone="critical" icon={<AlertTriangle className="h-3.5 w-3.5" />} sub="SLA 15m" />
        <StatCard label="Active Cases" value={metrics.activeCases} tone="primary" icon={<Briefcase className="h-3.5 w-3.5" />} />
        <StatCard label="SAR Generated" value={metrics.sar} tone="success" icon={<FileSignature className="h-3.5 w-3.5" />} />
        <StatCard label="Mule Accounts" value={metrics.mules} tone="warning" icon={<Users className="h-3.5 w-3.5" />} />
        <StatCard label="Network Risk" value={`${metrics.networkRisk}`} tone="critical" icon={<GitMerge className="h-3.5 w-3.5" />} sub="propagation score" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Panel title="Risk & Alert Trend (30 windows)" className="lg:col-span-2 h-64">
          {txnsQ.isLoading || alertsQ.isLoading || metricsQ.isLoading ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">Loading trend…</div>
          ) : txnsQ.isError || alertsQ.isError || metricsQ.isError ? (
            <div className="h-full flex items-center justify-center text-xs text-danger">Failed to load trend</div>
          ) : !riskTrendSeries.length ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No risk trend data available</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={riskTrendSeries} margin={{ top: 10, right: 8, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.7 0.18 240)" stopOpacity={0.6} />
                    <stop offset="100%" stopColor="oklch(0.7 0.18 240)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.62 0.24 22)" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="oklch(0.62 0.24 22)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--color-border)" strokeDasharray="2 4" />
                <XAxis dataKey="window" tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} />
                <YAxis tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", fontSize: 11 }} />
                <Area dataKey="risk" stroke="oklch(0.7 0.18 240)" fill="url(#g1)" strokeWidth={1.5} />
                <Area dataKey="alerts" stroke="oklch(0.62 0.24 22)" fill="url(#g2)" strokeWidth={1.5} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel title="Risk Distribution" className="h-64">
          {txnsQ.isLoading || alertsQ.isLoading ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">Loading distribution…</div>
          ) : txnsQ.isError || alertsQ.isError ? (
            <div className="h-full flex items-center justify-center text-xs text-danger">Failed to load distribution</div>
          ) : !riskDistribution.length ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No report distribution data available</div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={riskDistribution} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} stroke="var(--color-card)">
                    {riskDistribution.map((d, i) => <Cell key={i} fill={d.color} />)}
                  </Pie>
                  <Tooltip content={<PieRiskTooltip />} cursor={{ fill: "rgba(148, 163, 184, 0.08)" }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-1 text-[10px] mono px-2">
                {riskDistribution.map((d) => (
                  <div key={d.name} className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-sm" style={{ background: d.color }} />
                    <span className="text-muted-foreground">{d.name}</span>
                    <span className="ml-auto">{d.value.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Panel title="Channel Risk Composition" className="h-64 lg:col-span-2">
          {txnsQ.isLoading ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">Loading channels…</div>
          ) : txnsQ.isError ? (
            <div className="h-full flex items-center justify-center text-xs text-danger">Failed to load channel composition</div>
          ) : !channelRiskData.length ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No channel data available</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={channelRiskData} margin={{ top: 8, right: 8, left: -12, bottom: 4 }}>
                <CartesianGrid stroke="var(--color-border)" strokeDasharray="2 4" />
                <XAxis dataKey="name" tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} />
                <YAxis tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", fontSize: 11 }} />
                <Bar dataKey="risk" fill="oklch(0.7 0.18 240)">
                  {channelRiskData.map((d: any, i: number) => <Cell key={i} fill={d.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel title="Fraud Heatmap · day × hour" className="h-64">
          {txnsQ.isLoading ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">Loading heatmap…</div>
          ) : txnsQ.isError ? (
            <div className="h-full flex items-center justify-center text-xs text-danger">Failed to load heatmap</div>
          ) : !fraudHeatmap.length ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No heatmap data available</div>
          ) : (
            <div className="grid grid-rows-7 gap-0.5 h-full p-1">
              {fraudHeatmap.map((row: number[], ri: number) => (
                <div key={ri} className="grid grid-cols-24 gap-0.5" style={{ gridTemplateColumns: "repeat(24,1fr)" }}>
                  {row.map((v, ci) => (
                    <div
                      key={ci}
                      title={`${["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][ri]} ${ci}:00 · ${v}`}
                      className="rounded-[2px]"
                      style={{
                        background: v > 80 ? `oklch(0.62 0.24 22 / ${0.4 + v/200})`
                          : v > 50 ? `oklch(0.78 0.17 75 / ${0.3 + v/200})`
                          : `oklch(0.7 0.18 240 / ${0.1 + v/300})`,
                      }}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Panel title="Live Transaction Stream" subtitle="High-risk activity from last 60 seconds" className="lg:col-span-2 h-72" dense>
          <div className="overflow-y-auto scrollbar-thin h-full">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-card/90 backdrop-blur text-[10px] uppercase tracking-wider text-muted-foreground">
                <tr className="text-left">
                  <th className="px-3 py-1.5 font-medium">Time</th>
                  <th className="font-medium">Txn ID</th>
                  <th className="font-medium">Sender → Receiver</th>
                  <th className="font-medium text-right">Amount</th>
                  <th className="font-medium">Risk</th>
                  <th className="font-medium">Decision</th>
                </tr>
              </thead>
              <tbody>
                {dashboardTransactions.slice(0, 14).map((t, i) => (
                  <tr key={t.id} className={`border-t border-border/50 hover:bg-accent/30 ${i === 0 ? "row-enter" : ""}`}>
                    <td className="px-3 py-1.5 mono text-[10px] text-muted-foreground">{new Date(t.ts).toLocaleTimeString()}</td>
                    <td className="mono text-[10px]">{t.id.slice(0, 18)}</td>
                    <td className="text-[11px]"><span className="text-muted-foreground">{t.sender.slice(-7)}</span> <ArrowRight className="inline h-3 w-3 text-muted-foreground" /> {t.receiver.slice(-7)}</td>
                    <td className="text-right mono">{t.currency} {t.amount.toLocaleString()}</td>
                    <td><RiskScoreBadge score={t.riskScore} /></td>
                    <td><DecisionBadge d={t.decision} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Active Investigations" className="h-72" dense>
          <ul className="divide-y divide-border/50 overflow-y-auto h-full scrollbar-thin">
            {[
              { id: "CASE-7012", t: "Mule cluster · 14 accounts", p: "P1" as const, o: "A. Khan" },
              { id: "CASE-7008", t: "Cross-border layering EU→AE", p: "P1" as const, o: "M. Singh" },
              { id: "CASE-7003", t: "Synthetic identity onboarding", p: "P2" as const, o: "R. Costa" },
              { id: "CASE-6998", t: "Sanctions near-match", p: "P1" as const, o: "L. Park" },
              { id: "CASE-6991", t: "Crypto off-ramp", p: "P2" as const, o: "J. Werner" },
              { id: "CASE-6986", t: "Structuring sub-threshold", p: "P3" as const, o: "N. Adebayo" },
            ].map((c) => (
              <li key={c.id} className="p-2.5 flex items-center gap-2 hover:bg-accent/20">
                <PriorityBadge p={c.p} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs truncate">{c.t}</div>
                  <div className="text-[10px] text-muted-foreground mono">{c.id} · {c.o}</div>
                </div>
                <ShieldCheck className="h-3.5 w-3.5 text-muted-foreground" />
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
