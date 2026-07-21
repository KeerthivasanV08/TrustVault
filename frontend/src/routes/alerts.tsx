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
import { createCase } from '@/services/api/cases';
import { freeze as freezeAccount, sar as generateSar } from '@/services/api/officer';
import { API_BASE } from '@/services/api/client';
import { ArrowUpRight, CheckCircle2, FileSignature, Loader2, Snowflake, UserCheck, X } from "lucide-react";
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

  const [queue, setQueue] = useState<"ALL" | "AML_CRITICAL_QUEUE" | "AML_REVIEW_QUEUE" | "AML_MONITORING_QUEUE" | "AML_INFO_QUEUE">("ALL");
  const [selected, setSelected] = useState<Alert | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const refreshQueues = async () => {
    await queryClient.invalidateQueries();
  };

  const withBusy = async (key: string, task: () => Promise<void>) => {
    setBusyAction(key);
    try {
      await task();
    } finally {
      setBusyAction((current) => (current === key ? null : current));
    }
  };

  const triggerDownload = (downloadUrl: string) => {
    const absolute = new URL(downloadUrl, API_BASE).toString();
    const link = document.createElement('a');
    link.href = absolute;
    link.rel = 'noreferrer';
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    link.remove();
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
      source_alert_id: alert.id,
      source_alerts: [alert.id],
      evidence: alert.signals ?? [],
      created_at: new Date(alert.createdAt ?? Date.now()).toISOString(),
    });

    return created.caseId ?? created.id ?? created.case_id ?? '';
  };

  const handleAcknowledge = async (alertId: string) => {
    await withBusy(`ack:${alertId}`, async () => {
      try {
        await alertsQ.acknowledge(alertId);
        await refreshQueues();
        toast.success(`Acknowledged ${alertId}`);
      } catch (error) {
        toast.error(`Failed to acknowledge ${alertId}`);
      }
    });
  };

  const handleEscalate = async (alertId: string) => {
    await withBusy(`esc:${alertId}`, async () => {
      try {
        await alertsQ.escalate(alertId);
        await refreshQueues();
        toast.success(`Escalated ${alertId}`);
      } catch (error) {
        toast.error(`Failed to escalate ${alertId}`);
      }
    });
  };

  const handleFreeze = async (alert: Alert) => {
    await withBusy(`freeze:${alert.id}`, async () => {
      try {
        const caseId = await ensureCaseForAlert(alert);
        await freezeAccount({
          user_id: alert.userId,
          case_id: caseId,
          officer_id: 'OFFICER_1',
          freeze_type: 'DEBIT_FREEZE',
          reason: alert.summary ?? `Freeze requested for alert ${alert.id}`,
        });
        await refreshQueues();
        toast.success(`Freeze requested for ${alert.userId}`);
      } catch (error) {
        toast.error(`Failed to freeze alert ${alert.id}`);
      }
    });
  };

  const handleSar = async (alert: Alert) => {
    await withBusy(`sar:${alert.id}`, async () => {
      try {
        const caseId = await ensureCaseForAlert(alert);
        let result: any;

        try {
          result = await generateSar({
            case_id: caseId,
            officer_id: 'OFFICER_1',
            notes: alert.summary ?? `SAR requested from alert ${alert.id}`,
            filing_type: 'INTERNAL',
          }, 60000);
        } catch (firstError) {
          try {
            result = await generateSar({
              alert_id: alert.id,
              officer_id: 'OFFICER_1',
              notes: alert.summary ?? `SAR requested from alert ${alert.id}`,
              filing_type: 'INTERNAL',
            }, 60000);
          } catch (fallbackError) {
            console.error('SAR generation failed for alert', alert.id, { firstError, fallbackError });
            throw fallbackError;
          }
        }

        const downloadUrl = (result as any)?.download_url;
        if (downloadUrl) {
          triggerDownload(downloadUrl);
        }
        toast.success(`SAR generated for alert ${alert.id}`);
        refreshQueues().catch(() => undefined);
      } catch (error) {
        console.error('Failed to create SAR for alert', alert.id, error);
        const message = error instanceof Error ? error.message : String(error ?? 'Unknown error');
        toast.error(`Failed to create SAR for alert ${alert.id}: ${message}`);
      }
    });
  };

  const handleClose = async (alertId: string) => {
    await withBusy(`close:${alertId}`, async () => {
      try {
        await alertsQ.close(alertId);
        await refreshQueues();
        toast.success(`Closed ${alertId}`);
      } catch (error) {
        toast.error(`Failed to close ${alertId}`);
      }
    });
  };

  const filtered = alerts.filter((a) => queue === "ALL" || a.queue === queue);
  const counts = {
    ALL: alerts.length,
    AML_CRITICAL_QUEUE: alerts.filter((a) => a.queue === "AML_CRITICAL_QUEUE").length,
    AML_REVIEW_QUEUE: alerts.filter((a) => a.queue === "AML_REVIEW_QUEUE").length,
    AML_MONITORING_QUEUE: alerts.filter((a) => a.queue === "AML_MONITORING_QUEUE").length,
    AML_INFO_QUEUE: alerts.filter((a) => a.queue === "AML_INFO_QUEUE").length,
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
        {(["ALL", "AML_CRITICAL_QUEUE", "AML_REVIEW_QUEUE", "AML_MONITORING_QUEUE", "AML_INFO_QUEUE"] as const).map((q) => (
          <button key={q} onClick={() => setQueue(q)} className={`h-8 px-3 rounded-md mono border ${queue === q ? "bg-primary text-primary-foreground border-primary" : "border-border bg-card/60 hover:bg-card"}`}>
            {q === "ALL" ? q : q.split("_").join(" ")} <span className="opacity-60 ml-1">{counts[q]}</span>
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
                  <td className="mono text-[10px] text-muted-foreground">{a.createdAt ? new Date(a.createdAt).toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : "—"}</td>
                  <td><StatusBadge status={a.status} /></td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <div className="flex gap-1">
                      <ActionIcon icon={UserCheck} label="Acknowledge" onClick={() => handleAcknowledge(a.id)} loading={busyAction === `ack:${a.id}`} disabled={busyAction !== null && busyAction !== `ack:${a.id}`} />
                      <ActionIcon icon={ArrowUpRight} label="Escalate" onClick={() => handleEscalate(a.id)} tone="warning" loading={busyAction === `esc:${a.id}`} disabled={busyAction !== null && busyAction !== `esc:${a.id}`} />
                      <ActionIcon icon={Snowflake} label="Freeze account" onClick={() => handleFreeze(a)} tone="critical" loading={busyAction === `freeze:${a.id}`} disabled={busyAction !== null && busyAction !== `freeze:${a.id}`} />
                      <ActionIcon icon={FileSignature} label="Create SAR" onClick={() => handleSar(a)} tone="primary" loading={busyAction === `sar:${a.id}`} disabled={busyAction !== null && busyAction !== `sar:${a.id}`} />
                      <ActionIcon icon={CheckCircle2} label="Close" onClick={() => handleClose(a.id)} tone="success" loading={busyAction === `close:${a.id}`} disabled={busyAction !== null && busyAction !== `close:${a.id}`} />
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

function ActionIcon({ icon: Icon, label, onClick, tone = "default", disabled = false, loading = false }: { icon: any; label: string; onClick: () => void; tone?: "default" | "warning" | "critical" | "primary" | "success"; disabled?: boolean; loading?: boolean }) {
  const t = {
    default: "text-muted-foreground hover:text-foreground hover:bg-accent",
    warning: "text-warning hover:bg-warning/10",
    critical: "text-critical hover:bg-critical/10",
    primary: "text-primary hover:bg-primary/10",
    success: "text-success hover:bg-success/10",
  }[tone];
  return (
    <button onClick={onClick} title={label} disabled={disabled || loading} className={`h-6 w-6 rounded border border-border flex items-center justify-center transition ${t} ${(disabled || loading) ? 'opacity-50 cursor-not-allowed' : ''}`}>
      {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Icon className="h-3 w-3" />}
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
