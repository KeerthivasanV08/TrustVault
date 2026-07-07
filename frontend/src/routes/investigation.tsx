import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Panel } from "@/components/aml/Panel";
import { useAccount, useAccountList } from '@/hooks/useAccounts';
import { useRecentTransactions } from '@/hooks/useTransactions';
import { useAlerts } from '@/hooks/useAlerts';
import { useCases } from '@/hooks/useCases';
import { useAccountGraph } from '@/hooks/useGraph';
import { RiskScoreBadge } from "@/components/aml/Badges";
import { ArrowLeftRight, CheckCircle2, Smartphone, Wifi, XCircle } from "lucide-react";

export const Route = createFileRoute("/investigation")({
  head: () => ({ meta: [{ title: "Investigation Sandbox — TrustVault" }] }),
  component: InvestigationPage,
});

function InvestigationPage() {
  const [queryA, setQueryA] = useState("");
  const [queryB, setQueryB] = useState("");
  const [selectedAId, setSelectedAId] = useState<string | null>(null);
  const [selectedBId, setSelectedBId] = useState<string | null>(null);

  const accountsA = useAccountList({ limit: 25, search: queryA || undefined });
  const accountsB = useAccountList({ limit: 25, search: queryB || undefined });
  const accountA = useAccount(selectedAId ?? undefined);
  const accountB = useAccount(selectedBId ?? undefined);
  const alertsQ = useAlerts();
  const casesQ = useCases();
  const txnsQ = useRecentTransactions();
  const graphA = useAccountGraph(selectedAId ?? undefined);
  const graphB = useAccountGraph(selectedBId ?? undefined);

  const a = accountA.data;
  const b = accountB.data;
  const alerts = alertsQ.data ?? [];
  const cases = casesQ.data ?? [];
  const txns = txnsQ.data ?? [];

  const alertsA = useMemo(
    () => (a ? alerts.filter((alert) => alert.userId === a.id || alert.userId === a.id) : []),
    [a, alerts],
  );
  const alertsB = useMemo(
    () => (b ? alerts.filter((alert) => alert.userId === b.id || alert.userId === b.id) : []),
    [b, alerts],
  );

  const alertTypesA = useMemo(() => new Set(alertsA.map((alert) => alert.type)), [alertsA]);
  const alertTypesB = useMemo(() => new Set(alertsB.map((alert) => alert.type)), [alertsB]);
  const commonAlertTypes = useMemo(
    () => [...alertTypesA].filter((type) => alertTypesB.has(type)),
    [alertTypesA, alertTypesB],
  );

  const caseIdsA = useMemo(
    () => new Set(alertsA.flatMap((alert) => [alert.id, alert.alertId ?? ""]).filter(Boolean)),
    [alertsA],
  );
  const caseIdsB = useMemo(
    () => new Set(alertsB.flatMap((alert) => [alert.id, alert.alertId ?? ""]).filter(Boolean)),
    [alertsB],
  );
  const casesA = useMemo(
    () => cases.filter((cs) =>
      cs.sourceAlerts?.some((id) => caseIdsA.has(id)) || (cs.sourceAlert ? caseIdsA.has(cs.sourceAlert) : false),
    ),
    [cases, caseIdsA],
  );
  const casesB = useMemo(
    () => cases.filter((cs) =>
      cs.sourceAlerts?.some((id) => caseIdsB.has(id)) || (cs.sourceAlert ? caseIdsB.has(cs.sourceAlert) : false),
    ),
    [cases, caseIdsB],
  );
  const commonCases = useMemo(
    () => casesA.filter((caseItem) => casesB.some((other) => other.id === caseItem.id)),
    [casesA, casesB],
  );

  const txnsA = useMemo(
    () => (a ? txns.filter((txn) => txn.sender === a.id || txn.receiver === a.id) : []),
    [a, txns],
  );
  const txnsB = useMemo(
    () => (b ? txns.filter((txn) => txn.sender === b.id || txn.receiver === b.id) : []),
    [b, txns],
  );

  const counterpartiesA = useMemo(
    () => new Set(txnsA.map((txn) => (txn.sender === a?.id ? txn.receiver : txn.sender)).filter(Boolean)),
    [txnsA, a?.id],
  );
  const counterpartiesB = useMemo(
    () => new Set(txnsB.map((txn) => (txn.sender === b?.id ? txn.receiver : txn.sender)).filter(Boolean)),
    [txnsB, b?.id],
  );
  const sharedCounterparties = useMemo(
    () => new Set([...counterpartiesA].filter((counterparty) => counterpartiesB.has(counterparty))),
    [counterpartiesA, counterpartiesB],
  );

  const commonReceivers = useMemo(
    () => {
      if (!a || !b) return [] as string[];
      const aReceivers = new Set(txnsA.filter((txn) => txn.sender === a.id).map((txn) => txn.receiver));
      const bReceivers = new Set(txnsB.filter((txn) => txn.sender === b.id).map((txn) => txn.receiver));
      return [...aReceivers].filter((id) => bReceivers.has(id));
    },
    [a, b, txnsA, txnsB],
  );
  const commonSenders = useMemo(
    () => {
      if (!a || !b) return [] as string[];
      const aSenders = new Set(txnsA.filter((txn) => txn.receiver === a.id).map((txn) => txn.sender));
      const bSenders = new Set(txnsB.filter((txn) => txn.receiver === b.id).map((txn) => txn.sender));
      return [...aSenders].filter((id) => bSenders.has(id));
    },
    [a, b, txnsA, txnsB],
  );

  const graphNodesA = useMemo(
    () => new Set(graphA.data?.nodes?.map((node) => node.id) ?? []),
    [graphA.data?.nodes],
  );
  const graphNodesB = useMemo(
    () => new Set(graphB.data?.nodes?.map((node) => node.id) ?? []),
    [graphB.data?.nodes],
  );
  const commonGraphNodes = useMemo(
    () => [...graphNodesA].filter((id) => graphNodesB.has(id) && id !== selectedAId && id !== selectedBId),
    [graphNodesA, graphNodesB, selectedAId, selectedBId],
  );

  const sharedSignals = useMemo(() => {
    if (!a || !b) return [];
    return [
      {
        label: "Device ID",
        valueA: a.device_id ?? "—",
        valueB: b.device_id ?? "—",
        match: !!a.device_id && !!b.device_id && a.device_id === b.device_id,
        impact: "High",
      },
      {
        label: "IP Address",
        valueA: a.ip_address ?? "—",
        valueB: b.ip_address ?? "—",
        match: !!a.ip_address && !!b.ip_address && a.ip_address === b.ip_address,
        impact: "High",
      },
      {
        label: "Shared counterparties",
        valueA: sharedCounterparties.size ? [...sharedCounterparties].join(", ") : "None",
        valueB: sharedCounterparties.size ? [...sharedCounterparties].join(", ") : "None",
        match: sharedCounterparties.size > 0,
        impact: "High",
      },
      {
        label: "Common alert types",
        valueA: alertTypesA.size ? [...alertTypesA].join(", ") : "None",
        valueB: alertTypesB.size ? [...alertTypesB].join(", ") : "None",
        match: commonAlertTypes.length > 0,
        impact: "Medium",
      },
      {
        label: "Common cases",
        valueA: casesA.map((cs) => cs.title).join(", ") || "None",
        valueB: casesB.map((cs) => cs.title).join(", ") || "None",
        match: commonCases.length > 0,
        impact: "Medium",
      },
      {
        label: "Common graph nodes",
        valueA: commonGraphNodes.length ? `${commonGraphNodes.length} nodes` : "None",
        valueB: commonGraphNodes.length ? `${commonGraphNodes.length} nodes` : "None",
        match: commonGraphNodes.length > 0,
        impact: "Medium",
      },
      {
        label: "Common receivers",
        valueA: commonReceivers.length ? commonReceivers.join(", ") : "None",
        valueB: commonReceivers.length ? commonReceivers.join(", ") : "None",
        match: commonReceivers.length > 0,
        impact: "Low",
      },
      {
        label: "Common senders",
        valueA: commonSenders.length ? commonSenders.join(", ") : "None",
        valueB: commonSenders.length ? commonSenders.join(", ") : "None",
        match: commonSenders.length > 0,
        impact: "Low",
      },
    ];
  }, [a, b, sharedCounterparties, alertTypesA, alertTypesB, commonAlertTypes, casesA, casesB, commonCases, commonGraphNodes, commonReceivers, commonSenders]);

  const similarityScore = useMemo(() => {
    if (!a || !b) return undefined;
    const weights = [
      sharedSignals[0].match ? 3 : 0,
      sharedSignals[1].match ? 3 : 0,
      sharedSignals[2].match ? 3 : 0,
      sharedSignals[3].match ? 2 : 0,
      sharedSignals[4].match ? 2 : 0,
      sharedSignals[5].match ? 2 : 0,
      sharedSignals[6].match ? 1 : 0,
      sharedSignals[7].match ? 1 : 0,
    ];
    const totalWeight = 17;
    const score = weights.reduce((sum, weight) => sum + weight, 0) / totalWeight;
    return Number(score.toFixed(2));
  }, [a, b, sharedSignals]);

  const recentSharedTransactions = useMemo(() => {
    if (!a || !b) return [] as typeof txns;
    return txns
      .filter((txn) => sharedCounterparties.has(txn.sender === a.id ? txn.receiver : txn.sender) || sharedCounterparties.has(txn.sender === b.id ? txn.receiver : txn.sender))
      .slice(0, 5);
  }, [a, b, sharedCounterparties, txns]);

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Investigation Sandbox</h1>
          <p className="text-xs text-muted-foreground">Compare entities · graph overlap · shared-signal forensics</p>
        </div>
        <div className="flex items-center gap-2 text-[11px] mono">
          {similarityScore != null ? (
            <span className="px-2 py-1 rounded border border-warning/40 text-warning bg-warning/5">SIMILARITY {similarityScore}</span>
          ) : (
            <span className="px-2 py-1 rounded border border-border text-muted-foreground bg-card/50">Select two accounts</span>
          )}
          <span className={`px-2 py-1 rounded border ${similarityScore && similarityScore >= 0.5 ? "border-critical/40 text-critical bg-critical/5" : "border-border text-muted-foreground bg-card/50"}`}>
            {similarityScore != null ? (similarityScore >= 0.5 ? "LINKED EVIDENCE" : "LOW LINK EVIDENCE") : "Awaiting selection"}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Entity A">
          <div className="space-y-3">
            <LabelledSearch
              label="Search Entity A"
              value={queryA}
              onChange={setQueryA}
              options={accountsA.data?.results ?? []}
              selectedId={selectedAId}
              onSelectId={setSelectedAId}
            />
            {a ? (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-full bg-gradient-to-br from-primary to-info flex items-center justify-center text-base font-bold text-primary-foreground">{a.name?.split(" ").map((n) => n[0]).join("")}</div>
                  <div>
                    <div className="text-sm font-semibold">{a.name}</div>
                    <div className="text-[11px] mono text-muted-foreground">{a.country} · opened {new Date(a.openedAt ?? Date.now()).toLocaleDateString()}</div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-[11px]">
                  <Cell label="Device" v={a.device_id ?? "—"} mono />
                  <Cell label="IP" v={a.ip_address ?? "—"} mono />
                  <Cell label="Graph" v={a.graphProximity ?? 0} />
                  <Cell label="SIM" v={a.simRisk ?? 0} />
                  <Cell label="Alerts" v={alertsA.length} />
                  <Cell label="Cases" v={casesA.length} />
                </div>
              </div>
            ) : (
              <div className="rounded-md border border-border bg-card/40 p-3 text-xs text-muted-foreground">Select Entity A from backend account search to load details.</div>
            )}
          </div>
        </Panel>

        <Panel title="Entity B">
          <div className="space-y-3">
            <LabelledSearch
              label="Search Entity B"
              value={queryB}
              onChange={setQueryB}
              options={accountsB.data?.results ?? []}
              selectedId={selectedBId}
              onSelectId={setSelectedBId}
            />
            {b ? (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-full bg-gradient-to-br from-primary to-info flex items-center justify-center text-base font-bold text-primary-foreground">{b.name?.split(" ").map((n) => n[0]).join("")}</div>
                  <div>
                    <div className="text-sm font-semibold">{b.name}</div>
                    <div className="text-[11px] mono text-muted-foreground">{b.country} · opened {new Date(b.openedAt ?? Date.now()).toLocaleDateString()}</div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-[11px]">
                  <Cell label="Device" v={b.device_id ?? "—"} mono />
                  <Cell label="IP" v={b.ip_address ?? "—"} mono />
                  <Cell label="Graph" v={b.graphProximity ?? 0} />
                  <Cell label="SIM" v={b.simRisk ?? 0} />
                  <Cell label="Alerts" v={alertsB.length} />
                  <Cell label="Cases" v={casesB.length} />
                </div>
              </div>
            ) : (
              <div className="rounded-md border border-border bg-card/40 p-3 text-xs text-muted-foreground">Select Entity B from backend account search to load details.</div>
            )}
          </div>
        </Panel>
      </div>

      <Panel title="Shared Signal Matching">
        {a && b ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {sharedSignals.map((signal) => (
              <div key={signal.label} className={`rounded-md border p-3 ${signal.match ? "border-critical/30 bg-critical/5" : "border-border bg-card/40"}`}>
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs font-medium">{signal.label}</div>
                  {signal.match ? <CheckCircle2 className="h-4 w-4 text-critical" /> : <XCircle className="h-4 w-4 text-muted-foreground" />}
                </div>
                <div className="mt-2 text-[10px] text-muted-foreground">Entity A</div>
                <div className="text-sm font-semibold break-words">{signal.valueA}</div>
                <div className="mt-2 text-[10px] text-muted-foreground">Entity B</div>
                <div className="text-sm font-semibold break-words">{signal.valueB}</div>
                <div className="mt-2 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Risk impact</div>
                <div className="text-[11px]">{signal.impact}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-border bg-card/40 p-3 text-xs text-muted-foreground">Select two accounts to compare</div>
        )}
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Graph Overlap" subtitle="Common neighbors at depth ≤ 2">
          {a && b ? (
            commonGraphNodes.length ? (
              <div className="space-y-3">
                <div className="text-sm font-semibold">Shared infrastructure nodes</div>
                <div className="grid grid-cols-1 gap-2 text-xs">
                  {commonGraphNodes.slice(0, 6).map((nodeId) => (
                    <div key={nodeId} className="rounded-md border border-border bg-card/40 p-2 break-words">{nodeId}</div>
                  ))}
                </div>
                <div className="text-[11px] text-muted-foreground">Graph proximity derived from shared node overlap.</div>
              </div>
            ) : (
              <div className="rounded-md border border-border bg-card/40 p-3 text-xs text-muted-foreground">No shared signals found in graph overlap</div>
            )
          ) : (
            <div className="rounded-md border border-border bg-card/40 p-3 text-xs text-muted-foreground">Select two accounts to compare</div>
          )}
        </Panel>

        <Panel title="Transaction Overlap (recent)" dense>
          {a && b ? (
            sharedCounterparties.length ? (
              <div className="space-y-3">
                <div className="grid grid-cols-1 gap-2 text-xs">
                  <div className="rounded-md border border-border bg-card/40 p-2">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Overlapping counterparties</div>
                    <div className="mt-1 break-words">{sharedCounterparties.join(', ')}</div>
                  </div>
                  <div className="rounded-md border border-border bg-card/40 p-2">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Common senders</div>
                    <div className="mt-1 break-words">{commonSenders.length ? commonSenders.join(', ') : 'None'}</div>
                  </div>
                  <div className="rounded-md border border-border bg-card/40 p-2">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Common receivers</div>
                    <div className="mt-1 break-words">{commonReceivers.length ? commonReceivers.join(', ') : 'None'}</div>
                  </div>
                </div>
                <div className="text-[11px] text-muted-foreground">Recent transaction patterns involving shared counterparties.</div>
                <ul className="divide-y divide-border/50 text-xs">
                  {recentSharedTransactions.map((txn) => (
                    <li key={txn.id} className="px-3 py-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ArrowLeftRight className="h-3 w-3 text-warning" />
                        <span className="mono">{txn.sender} → {txn.receiver}</span>
                      </div>
                      <span className="mono">{txn.currency} {txn.amount.toLocaleString()}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="rounded-md border border-border bg-card/40 p-3 text-xs text-muted-foreground">No overlapping transactions available from backend</div>
            )
          ) : (
            <div className="rounded-md border border-border bg-card/40 p-3 text-xs text-muted-foreground">Select two accounts to compare</div>
          )}
        </Panel>
      </div>
    </div>
  );
}

function LabelledSearch({
  label,
  value,
  onChange,
  options,
  selectedId,
  onSelectId,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { id: string; name?: string }[];
  selectedId: string | null;
  onSelectId: (id: string | null) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search accounts by id or name"
        className="w-full rounded-md border border-border bg-input/60 px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
      />
      <select
        value={selectedId ?? ""}
        onChange={(event) => onSelectId(event.target.value || null)}
        className="w-full rounded-md border border-border bg-card/60 px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
      >
        <option value="">Select account</option>
        {options.map((account) => (
          <option key={account.id} value={account.id}>
            {account.id} {account.name ? `· ${account.name}` : ''}
          </option>
        ))}
      </select>
    </div>
  );
}

function Cell({ label, v, mono }: { label: string; v: React.ReactNode; mono?: boolean }) {
  return (
    <div className="rounded-md border border-border bg-card/40 p-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-0.5 text-xs ${mono ? "mono" : ""}`}>{v}</div>
    </div>
  );
}
