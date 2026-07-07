import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useStore, mergeHistoricalAlerts } from "@/store/realtime";
import { Panel } from "@/components/aml/Panel";
import { PriorityBadge, RiskScoreBadge, StatusBadge } from "@/components/aml/Badges";
import { SLATimer } from "@/components/aml/SLATimer";
import type { Alert } from '@/types';
import { ExplainabilityPanel } from "@/components/aml/ExplainabilityPanel";
import { useAlerts } from '@/hooks/useAlerts';
import { createCase, freezeCase, sarCase } from '@/services/api/cases';
import { ArrowUpRight, CheckCircle2, FileSignature, Snowflake, UserCheck, X } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/alerts")({
  head: () => ({ meta: [{ title: "Alert Center — TrustVault" }] }),
  component: AlertsPage,
});

function AlertsPage() {
  const alerts = useStore((s) => s.alerts);
  const alertsQ = useAlerts();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (alertsQ.data && !alertsQ.isFetching) mergeHistoricalAlerts(alertsQ.data || []);
  }, [alertsQ.data, alertsQ.isFetching]);

  const [queue, setQueue] = useState<"ALL" | "P1_QUEUE" | "ESCALATED" | "EDD" | "GENERAL">("ALL");
  const [selected, setSelected] = useState<Alert | null>(null);

  const refreshQueues = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['alerts', 'list'] }),
      queryClient.invalidateQueries({ queryKey: ['alerts', 'p1'] }),
      queryClient.invalidateQueries({ queryKey: ['cases', 'list'] }),
    ]);
  };

  const ensureCaseForAlert = async (alert: Alert) => {
    if (alert.caseId) {
      return alert.caseId;
    }

    const created = await createCase({
      case_id: `CASE-${alert.id}`,
      title: alert.summary ? `Alert ${alert.id}: ${alert.summary}` : `Manual review for alert ${alert.id}`,
      priority: alert.priority,
      status: 'OPEN',
      source_alert: alert.id,
      source_alerts: [alert.id],
      evidence: alert.signals ?? [],
      created_at: new Date(alert.createdAt ?? Date.now()).toISOString(),
    });

    return created.caseId ?? created.id;
  };

  const handleAcknowledge = async (alertId: string) => {
    try {
      await alertsQ.acknowledge(alertId);
      await refreshQueues();
      toast.success(`Acknowledged ${alertId}`);
    } catch (error) {
      toast.error(`Failed to acknowledge ${alertId}`);
    }
  };

  const handleEscalate = async (alertId: string) => {
    try {
      await alertsQ.escalate(alertId);
      await refreshQueues();
      toast.success(`Escalated ${alertId}`);
    } catch (error) {
      toast.error(`Failed to escalate ${alertId}`);
    }
  };

  const handleFreeze = async (alert: Alert) => {
    try {
      const caseId = await ensureCaseForAlert(alert);
      await freezeCase(caseId);
      await refreshQueues();
      toast.success(`Freeze requested for case ${caseId}`);
    } catch (error) {
      toast.error(`Failed to freeze alert ${alert.id}`);
    }
  };

  const handleSar = async (alert: Alert) => {
    try {
      const caseId = await ensureCaseForAlert(alert);
      await sarCase(caseId);
      await refreshQueues();
      toast.success(`SAR requested for case ${caseId}`);
    } catch (error) {
      toast.error(`Failed to create SAR for alert ${alert.id}`);
    }
  };

  const handleClose = async (alertId: string) => {
    try {
      await alertsQ.close(alertId);
      await refreshQueues();
      toast.success(`Closed ${alertId}`);
    } catch (error) {
      toast.error(`Failed to close ${alertId}`);
    }
  };

  const filtered = alerts.filter((a) => queue === "ALL" || a.queue === queue);
  const counts = {
    ALL: alerts.length,
    P1_QUEUE: alerts.filter((a) => a.queue === "P1_QUEUE").length,
    ESCALATED: alerts.filter((a) => a.queue === "ESCALATED").length,
    EDD: alerts.filter((a) => a.queue === "EDD").length,
    GENERAL: alerts.filter((a) => a.queue === "GENERAL").length,
  };

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Alert Center</h1>
          <p className="text-xs text-muted-foreground">Operational alert queue · SLA-driven prioritization · auto-routing engine v2.4</p>
        </div>
      </div>

      {alertsQ.isError && (
        <div className="rounded-md border border-danger/40 bg-danger/5 px-3 py-2 text-xs text-danger">
          Backend unavailable. Alerts could not be loaded.
        </div>
      )}

      <div className="flex items-center gap-1.5 text-[11px]">
        {(["ALL", "P1_QUEUE", "ESCALATED", "EDD", "GENERAL"] as const).map((q) => (
          <button key={q} onClick={() => setQueue(q)} className={`h-8 px-3 rounded-md mono border ${queue === q ? "bg-primary text-primary-foreground border-primary" : "border-border bg-card/60 hover:bg-card"}`}>
            {q.replace("_", " ")} <span className="opacity-60 ml-1">{counts[q]}</span>
          </button>
        ))}
      </div>

      <Panel title={`${filtered.length} alerts in queue`} dense>
        {alertsQ.isLoading && !alerts.length ? (
          <div className="h-40 flex items-center justify-center text-xs text-muted-foreground">Loading alerts…</div>
        ) : !filtered.length ? (
          <div className="h-40 flex items-center justify-center text-xs text-muted-foreground">No alerts available from backend</div>
        ) : (
        <div className="overflow-auto scrollbar-thin max-h-[calc(100vh-260px)]">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-card/95 backdrop-blur text-[10px] uppercase tracking-wider text-muted-foreground z-10">
              <tr className="text-left border-b border-border">
                {["Pri", "Alert ID", "Type", "User", "Risk", "Queue", "Officer", "SLA", "Created", "Status", "Actions"].map((h) => (
                  <th key={h} className="px-2 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 80).map((a) => (
                <tr key={a.id} onClick={() => setSelected(a)} className={`border-b border-border/50 cursor-pointer hover:bg-accent/30 ${a.priority === "P1" ? "bg-critical/[0.04]" : ""}`}>
                  <td className="px-2 py-1.5"><PriorityBadge p={a.priority} /></td>
                  <td className="mono text-[11px]">{a.id}</td>
                  <td>{a.type}</td>
                  <td><div className="mono text-[10px]">{a.userId}</div><div className="text-muted-foreground text-[10px]">{a.userName}</div></td>
                  <td><RiskScoreBadge score={a.riskScore} /></td>
                  <td className="mono text-[10px] text-muted-foreground">{a.queue.replace("_", " ")}</td>
                  <td className="text-[11px]">{a.assignedOfficer ?? <span className="text-muted-foreground italic">unassigned</span>}</td>
                  <td><SLATimer dueAt={a.slaDueAt} /></td>
                  <td className="mono text-[10px] text-muted-foreground">{a.createdAt ? new Date(a.createdAt).toLocaleTimeString() : "—"}</td>
                  <td><StatusBadge status={a.status} /></td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <div className="flex gap-1">
                      <ActionIcon icon={UserCheck} label="Acknowledge" onClick={() => handleAcknowledge(a.id)} />
                      <ActionIcon icon={ArrowUpRight} label="Escalate" onClick={() => handleEscalate(a.id)} tone="warning" />
                      <ActionIcon icon={Snowflake} label="Freeze account" onClick={() => handleFreeze(a)} tone="critical" />
                      <ActionIcon icon={FileSignature} label="Create SAR" onClick={() => handleSar(a)} tone="primary" />
                      <ActionIcon icon={CheckCircle2} label="Close" onClick={() => handleClose(a.id)} tone="success" />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </Panel>

      {selected && <AlertDrawer a={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function ActionIcon({ icon: Icon, label, onClick, tone = "default" }: { icon: any; label: string; onClick: () => void; tone?: "default" | "warning" | "critical" | "primary" | "success" }) {
  const t = {
    default: "text-muted-foreground hover:text-foreground hover:bg-accent",
    warning: "text-warning hover:bg-warning/10",
    critical: "text-critical hover:bg-critical/10",
    primary: "text-primary hover:bg-primary/10",
    success: "text-success hover:bg-success/10",
  }[tone];
  return (
    <button onClick={onClick} title={label} className={`h-6 w-6 rounded border border-border flex items-center justify-center ${t}`}>
      <Icon className="h-3 w-3" />
    </button>
  );
}

function AlertDrawer({ a, onClose }: { a: Alert; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-background/60 backdrop-blur-sm" onClick={onClose} />
      <aside className="w-[600px] bg-card border-l border-border overflow-y-auto scrollbar-thin">
        <header className="sticky top-0 z-10 bg-card/95 backdrop-blur border-b border-border px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PriorityBadge p={a.priority} />
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Alert</div>
              <div className="mono text-sm">{a.id} · {a.type}</div>
            </div>
          </div>
          <button onClick={onClose} className="h-7 w-7 rounded hover:bg-accent flex items-center justify-center"><X className="h-4 w-4" /></button>
        </header>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <Field label="User" value={a.userId} />
            <Field label="Officer" value={a.assignedOfficer ?? "—"} />
            <Field label="SLA" value={<SLATimer dueAt={a.slaDueAt} />} />
            <Field label="Channel" value={a.channel} />
            <Field label="Amount" value={a.amount != null ? `$ ${a.amount.toLocaleString()}` : "—"} />
            <Field label="Status" value={<StatusBadge status={a.status} />} />
          </div>
          <ExplainabilityPanel finalScore={a.riskScore} decision={a.priority === "P1" ? "BLOCK" : "REVIEW"} />
        </div>
      </aside>
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border bg-card/40 p-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-0.5 mono text-xs">{value}</div>
    </div>
  );
}
