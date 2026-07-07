import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from '@tanstack/react-query';
import { Panel } from "@/components/aml/Panel";
import { PriorityBadge, RiskScoreBadge, StatusBadge, DecisionBadge } from "@/components/aml/Badges";
import { SLATimer } from "@/components/aml/SLATimer";
import { ExplainabilityPanel } from "@/components/aml/ExplainabilityPanel";
import type { Alert } from '@/types';
import { ArrowUpRight, CheckCircle2, FileSignature, Snowflake, ThumbsDown, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { useAlerts } from '@/hooks/useAlerts';
import { useCases, useAssignCase } from '@/hooks/useCases';
import { useOfficerActions } from '@/hooks/useOfficer';
import { closeAlert } from '@/services/api/alerts';
import { whitelistOfficer } from '@/services/api/officer';

const QUEUE_OPTIONS = [
  { id: "P1_QUEUE", label: "P1 — Critical", tone: "critical" as const, snapshotKey: "P1_QUEUE" },
  { id: "ESCALATED", label: "Escalated", tone: "warning" as const },
  { id: "EDD", label: "EDD Review", tone: "info" as const, snapshotKey: "EDD_QUEUE" },
  { id: "MANUAL_REVIEW", label: "Manual Review", tone: "default" as const, snapshotKey: "MANUAL_REVIEW_QUEUE" },
] as const;

type QueueKey = (typeof QUEUE_OPTIONS)[number]['id'];

type QueueItem = Alert;

export const Route = createFileRoute("/officer-review")({
  head: () => ({ meta: [{ title: "Officer Review — TrustVault" }] }),
  component: OfficerReview,
});

function OfficerReview() {
  const queryClient = useQueryClient();
  const alertsQ = useAlerts();
  const casesQ = useCases();
  const officerActions = useOfficerActions();
  const assignCase = useAssignCase();

  const [activeQueue, setActiveQueue] = useState<QueueKey>("P1_QUEUE");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const alerts = alertsQ.data ?? [];
  const alertQueue = alertsQ.queue.data;

  const queueItems = useMemo(() => {
    switch (activeQueue) {
      case 'P1_QUEUE':
        return alertsQ.p1.data ?? [];
      case 'ESCALATED':
        return alerts.filter((alert) => alert.status === 'ESCALATED' || alert.queue === 'ESCALATED');
      case 'EDD':
        return alerts.filter((alert) => alert.queue === 'EDD_QUEUE');
      case 'MANUAL_REVIEW':
        return alerts.filter((alert) => alert.queue === 'MANUAL_REVIEW_QUEUE');
      default:
        return [];
    }
  }, [activeQueue, alerts, alertsQ.p1.data]);

  useEffect(() => {
    if (!selectedId && queueItems.length) {
      setSelectedId(queueItems[0].id);
    }
  }, [queueItems, selectedId]);

  const selected = useMemo(() => alerts.find((alert) => alert.id === selectedId) ?? null, [alerts, selectedId]);

  const linkedAlerts = useMemo(() => {
    if (!selected) return [];
    return alerts.filter((alert) => alert.userId === selected.userId && alert.id !== selected.id).slice(0, 8);
  }, [alerts, selected]);

  const p1Count = alertsQ.p1.data?.length ?? 0;
  const escalatedCount = alerts.filter((alert) => alert.status === 'ESCALATED' || alert.queue === 'ESCALATED').length;
  const eddCount = alertQueue?.EDD_QUEUE?.size ?? 0;
  const manualCount = alertQueue?.MANUAL_REVIEW_QUEUE?.size ?? 0;
  const closedCount = casesQ.data?.filter((item) => item.status === 'CLOSED').length ?? 0;
  const sarCount = casesQ.data?.filter((item) => item.status === 'SAR_FILED').length ?? 0;

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ['alerts'] });
    queryClient.invalidateQueries({ queryKey: ['cases'] });
  };

  const handleFreeze = async () => {
    if (!selected?.userId) {
      toast.error('Select an alert with a user before freezing');
      return;
    }
    try {
      await officerActions.freeze({ user_id: selected.userId, case_id: selected.caseId ?? undefined, officer_id: 'OFFICER_1' });
      toast.success(`Freeze requested for ${selected.userId}`);
      refreshAll();
    } catch {
      toast.error('Freeze action failed');
    }
  };

  const handleEscalate = async () => {
    if (!selected?.caseId) {
      toast.error('Escalate requires a linked case');
      return;
    }
    try {
      await officerActions.escalate({ case_id: selected.caseId, officer_id: 'OFFICER_1' });
      toast.success(`Escalation sent for ${selected.caseId}`);
      refreshAll();
    } catch {
      toast.error('Escalation failed');
    }
  };

  const handleSar = async () => {
    if (!selected?.caseId) {
      toast.error('SAR generation requires a linked case');
      return;
    }
    try {
      await officerActions.sar({ case_id: selected.caseId, notes: 'Officer review SAR request' });
      toast.success(`SAR requested for ${selected.caseId}`);
      refreshAll();
    } catch {
      toast.error('SAR action failed');
    }
  };

  const handleAssign = async () => {
    if (!selected?.caseId) {
      toast.error('Assign requires a linked case');
      return;
    }
    try {
      await assignCase.mutateAsync({ id: selected.caseId, officerId: 'OFFICER_1' });
      toast.success(`Assigned case ${selected.caseId}`);
      refreshAll();
    } catch {
      toast.error('Case assignment failed');
    }
  };

  const handleWhitelist = async () => {
    if (!selected?.userId) {
      toast.error('Whitelist requires a user id');
      return;
    }
    try {
      await officerActions.whitelist({ user_id: selected.userId, reason: 'FALSE_POSITIVE', officer_id: 'OFFICER_1' });
      toast.success(`Marked ${selected.userId} as false positive`);
      refreshAll();
    } catch {
      toast.error('Whitelist action failed');
    }
  };

  const handleCloseAlert = async () => {
    if (!selected?.id) {
      toast.error('Select an alert to close');
      return;
    }
    try {
      await closeAlert(selected.id);
      toast.success(`Alert ${selected.id} closed`);
      refreshAll();
    } catch {
      toast.error('Close failed');
    }
  };

  return (
    <div className="p-4 space-y-3 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Officer Review Workbench</h1>
          <p className="text-xs text-muted-foreground">Investigation desk · officer <span className="mono text-foreground">OFFICER_1</span> · shift 09:00–17:00 UTC</p>
        </div>
        <div className="flex items-center gap-2 text-[11px] mono">
          <Pill label="Open" value={alerts.length} />
          <Pill label="Closed today" value={closedCount} tone="success" />
          <Pill label="SAR drafted" value={sarCount} tone="primary" />
        </div>
      </div>

      {(alertsQ.isError || casesQ.isError) && (
        <div className="rounded-md border border-danger/40 bg-danger/5 px-3 py-2 text-xs text-danger">
          Backend unavailable. Officer review data could not be fully loaded.
        </div>
      )}

      <div className="grid grid-cols-12 gap-3 flex-1 min-h-0">
        <div className="col-span-3 flex flex-col gap-3 min-h-0">
          <Panel title="Officer Queues" dense>
            <div className="flex flex-col">
              {QUEUE_OPTIONS.map((queueOption) => {
                const count = queueOption.id === 'P1_QUEUE'
                  ? p1Count
                  : queueOption.id === 'ESCALATED'
                  ? escalatedCount
                  : queueOption.id === 'EDD'
                  ? eddCount
                  : manualCount;
                return (
                  <button key={queueOption.id} onClick={() => setActiveQueue(queueOption.id)} className={`text-left px-3 py-2.5 border-l-2 flex items-center justify-between ${activeQueue === queueOption.id ? "bg-accent/40 border-primary" : "border-transparent hover:bg-accent/20"}`}>
                    <div>
                      <div className="text-xs font-medium">{queueOption.label}</div>
                      <div className="text-[10px] text-muted-foreground mono">{queueOption.id}</div>
                    </div>
                    <span className={`mono text-[11px] px-1.5 py-0.5 rounded border ${queueOption.tone === 'critical' ? 'border-critical/40 text-critical bg-critical/10' : queueOption.tone === 'warning' ? 'border-warning/40 text-warning bg-warning/10' : queueOption.tone === 'info' ? 'border-info/40 text-info bg-info/10' : 'border-border text-muted-foreground bg-card/60'}`}>{count}</span>
                  </button>
                );
              })}
            </div>
          </Panel>

          <Panel title={`Queue · ${activeQueue.replace("_", " ")}`} className="flex-1 min-h-0" dense>
            {alertsQ.isLoading && !queueItems.length ? (
              <div className="h-full flex items-center justify-center text-xs text-muted-foreground">Loading queue…</div>
            ) : !queueItems.length ? (
              <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No queue items available from backend</div>
            ) : (
              <ul className="overflow-y-auto scrollbar-thin h-full divide-y divide-border/50">
                {queueItems.slice(0, 30).map((alert) => (
                  <li key={alert.id} onClick={() => setSelectedId(alert.id)} className={`p-2.5 cursor-pointer hover:bg-accent/30 ${selected?.id === alert.id ? "bg-accent/40" : ""}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <PriorityBadge p={alert.priority} />
                      <span className="mono text-[11px]">{alert.alertId ?? alert.id}</span>
                      <SLATimer dueAt={alert.slaDueAt} />
                    </div>
                    <div className="text-xs">{alert.type}</div>
                    <div className="text-[10px] text-muted-foreground mono">{alert.userId} · {alert.assignedOfficer ?? 'unassigned'}</div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>

        <div className="col-span-6 flex flex-col gap-3 min-h-0">
          {selected ? (
            <>
              <Panel title="Investigation Card" subtitle={`${selected.alertId ?? selected.id} · ${selected.type}`}>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <Field label="Account / User" value={selected.userId} />
                  <Field label="Assigned officer" value={selected.assignedOfficer ?? 'Unassigned'} />
                  <Field label="Decision" value={<DecisionBadge d={selected.priority === 'P1' ? 'BLOCK' : 'REVIEW'} />} />
                  <Field label="SLA" value={<SLATimer dueAt={selected.slaDueAt} />} />
                  <Field label="Final risk score" value={<RiskScoreBadge score={selected.finalScore ?? selected.riskScore} />} />
                  <Field label="Alert status" value={<StatusBadge status={selected.status ?? 'OPEN'} />} />
                  <Field label="Behavioral score" value={formatScore(selected.behaviorScore)} />
                  <Field label="Sequence score" value={formatScore(selected.sequenceScore)} />
                  <Field label="Graph score" value={formatScore(selected.graphScore)} />
                  <Field label="Case" value={selected.caseId ?? 'No case linked'} />
                </div>
                <div className="mt-3 space-y-2">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Summary</div>
                  <div className="text-sm">{selected.summary ?? selected.type}</div>
                </div>
                {selected.reasons?.length ? (
                  <div className="mt-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Reasons / signals</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {selected.reasons.map((reason) => (
                        <span key={reason} className="text-[10px] mono px-2 py-1 rounded bg-card/60 border border-border">{reason}</span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </Panel>

              <div className="grid grid-cols-2 gap-3 flex-1 min-h-0">
                <Panel title="Evidence Timeline" dense>
                  <div className="overflow-y-auto scrollbar-thin h-full pr-2 text-xs">
                    <ol className="relative border-l border-border pl-4 space-y-3">
                      {((selected.evidence ?? selected.signals) ?? []).length ? ((selected.evidence ?? selected.signals) ?? []).map((item, index) => (
                        <li key={`${String(item)}-${index}`} className="relative">
                          <span className="absolute -left-[9px] top-1 h-2 w-2 rounded-full bg-primary" />
                          <div className="mono text-[10px] text-muted-foreground">Step {index + 1}</div>
                          <div>{item}</div>
                        </li>
                      )) : (
                        <li className="text-muted-foreground">No published evidence details available for this alert.</li>
                      )}
                      {selected.caseId ? <li className="text-[10px] text-muted-foreground mt-2">Linked case ID: {selected.caseId}</li> : null}
                    </ol>
                  </div>
                </Panel>
                <Panel title="Explainability" dense>
                  <div className="p-3 overflow-y-auto scrollbar-thin h-full">
                    <ExplainabilityPanel
                      finalScore={selected.finalScore ?? selected.riskScore}
                      decision={selected.priority === 'P1' ? 'BLOCK' : 'REVIEW'}
                    />
                  </div>
                </Panel>
              </div>
            </>
          ) : (
            <Panel className="flex-1"><div className="text-xs text-muted-foreground text-center pt-12">Select an alert from the queue</div></Panel>
          )}
        </div>

        <div className="col-span-3 flex flex-col gap-3 min-h-0">
          <Panel title="Operational Actions">
            <div className="space-y-2">
              <ActionBtn icon={Snowflake} label="Freeze Account" tone="critical" disabled={!selected?.userId || officerActions.freeze.isLoading} onClick={handleFreeze} />
              <ActionBtn icon={ArrowUpRight} label="Escalate to MLRO" tone="warning" disabled={!selected?.caseId || officerActions.escalate.isLoading} onClick={handleEscalate} />
              <ActionBtn icon={FileSignature} label="Generate SAR" tone="primary" disabled={!selected?.caseId || officerActions.sar.isLoading} onClick={handleSar} />
              <ActionBtn icon={UserPlus} label="Assign Case" tone="default" disabled={!selected?.caseId || assignCase.isLoading} onClick={handleAssign} />
              <ActionBtn icon={ThumbsDown} label="Mark False Positive" tone="default" disabled={!selected?.userId || officerActions.whitelist.isLoading} onClick={handleWhitelist} />
              <ActionBtn icon={CheckCircle2} label="Close Alert" tone="success" disabled={!selected?.id} onClick={handleCloseAlert} />
            </div>
          </Panel>

          <Panel title="Linked Alerts" className="flex-1 min-h-0" dense>
            <ul className="overflow-y-auto scrollbar-thin h-full divide-y divide-border/50">
              {linkedAlerts.length ? linkedAlerts.map((alert) => (
                <li key={alert.id} className="p-2 text-xs flex items-center gap-2">
                  <PriorityBadge p={alert.priority} />
                  <div className="flex-1 min-w-0">
                    <div className="mono text-[10px]">{alert.alertId ?? alert.id}</div>
                    <div className="text-[10px] text-muted-foreground truncate">{alert.type}</div>
                  </div>
                  <RiskScoreBadge score={alert.riskScore} />
                </li>
              )) : (
                <li className="p-3 text-xs text-muted-foreground">No linked alerts were found for the selected account.</li>
              )}
            </ul>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function formatScore(value?: number) {
  return value != null ? <span className="mono text-xs">{value.toFixed(1)}</span> : <span className="mono text-xs text-muted-foreground">N/A</span>;
}

function Pill({ label, value, tone = "default" }: { label: string; value: React.ReactNode; tone?: "default" | "success" | "primary" }) {
  const c = tone === "success" ? "border-success/40 text-success bg-success/5" : tone === "primary" ? "border-primary/40 text-primary bg-primary/5" : "border-border";
  return <span className={`px-2 py-1 rounded border ${c}`}>{label} <span className="mono ml-1">{value}</span></span>;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="rounded-md border border-border bg-card/40 p-2"><div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div><div className="mt-0.5 mono text-xs">{value}</div></div>;
}

function ActionBtn({ icon: Icon, label, tone, onClick, disabled }: { icon: any; label: string; tone?: string; onClick: () => void; disabled?: boolean }) {
  const t = tone === "critical" ? "border-critical/40 text-critical hover:bg-critical/10"
    : tone === "warning" ? "border-warning/40 text-warning hover:bg-warning/10"
    : tone === "primary" ? "border-primary/40 text-primary hover:bg-primary/10"
    : tone === "success" ? "border-success/40 text-success hover:bg-success/10"
    : "border-border hover:bg-accent";
  return (
    <button disabled={disabled} onClick={onClick} className={`w-full h-9 px-3 rounded-md border flex items-center gap-2 text-xs font-medium ${t} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
      <Icon className="h-3.5 w-3.5" /> <span>{label}</span>
    </button>
  );
}
