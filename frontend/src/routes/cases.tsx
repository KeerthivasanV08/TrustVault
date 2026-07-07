import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Panel } from "@/components/aml/Panel";
import { PriorityBadge, StatusBadge } from "@/components/aml/Badges";
import { SLATimer } from "@/components/aml/SLATimer";
import type { Case as CaseType } from '@/types';
import { useCases, useAssignCase, useFreezeCase, useSarCase, useCreateCase } from '@/hooks/useCases';
import { useAlerts } from '@/hooks/useAlerts';
import { Briefcase, CheckCircle2, FileText, Plus, Snowflake, X } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/cases")({
  head: () => ({ meta: [{ title: "Case Registry — TrustVault" }] }),
  component: CasesPage,
});

function CasesPage() {
  const [selected, setSelected] = useState<CaseType | null>(null);
  const [status, setStatus] = useState<"ALL" | CaseType["status"]>("ALL");
  const { data: list = [], isLoading, isError } = useCases();
  const alertsQ = useAlerts();
  const queryClient = useQueryClient();
  const createCase = useCreateCase();
  const assignCase = useAssignCase();
  const freezeCase = useFreezeCase();
  const sarCase = useSarCase();

  const filtered = list.filter((c) => status === "ALL" || c.status === status);

  const handleAssign = async () => {
    if (!selected) return;
    try {
      await assignCase.mutateAsync({ id: selected.id, officerId: "A. Khan" });
      await queryClient.invalidateQueries({ queryKey: ['cases', 'list'] });
      toast.success(`Assigned ${selected.id}`);
    } catch (error) {
      toast.error(`Failed to assign ${selected.id}`);
    }
  };

  const handleFreeze = async () => {
    if (!selected) return;
    try {
      await freezeCase.mutateAsync(selected.id);
      await queryClient.invalidateQueries({ queryKey: ['cases', 'list'] });
      toast.success(`Freeze requested for ${selected.id}`);
    } catch (error) {
      toast.error(`Failed to freeze ${selected.id}`);
    }
  };

  const handleSar = async () => {
    if (!selected) return;
    try {
      await sarCase.mutateAsync(selected.id);
      await queryClient.invalidateQueries({ queryKey: ['cases', 'list'] });
      toast.success(`SAR generated for ${selected.id}`);
    } catch (error) {
      toast.error(`Failed to generate SAR for ${selected.id}`);
    }
  };

  const handleNewCase = async () => {
    const sourceAlert = alertsQ.data?.[0]?.alertId ?? alertsQ.data?.[0]?.id;
    if (!sourceAlert) {
      toast.error('No alerts available to create a case.');
      return;
    }

    try {
      const created = await createCase.mutateAsync({
        case_id: `CASE-${Date.now()}`,
        title: 'Manual AML investigation case',
        priority: 'P3',
        status: 'OPEN',
        source_alert: sourceAlert,
        source_alerts: [sourceAlert],
        evidence: ['Created from UI'],
        created_at: new Date().toISOString(),
      });

      await queryClient.invalidateQueries({ queryKey: ['cases', 'list'] });
      setSelected(created);
      toast.success(`Created ${created.id}`);
    } catch (error) {
      toast.error('Failed to create case');
    }
  };

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Case Registry</h1>
          <p className="text-xs text-muted-foreground">Investigation registry · {list.length} cases · {list.filter((c) => c.status === "SAR_FILED").length} SARs filed</p>
        </div>
        <button onClick={handleNewCase} className="h-8 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium flex items-center gap-1.5"><Plus className="h-3.5 w-3.5" /> New Case</button>
      </div>

      {isError && <div className="rounded-md border border-danger/40 bg-danger/5 px-3 py-2 text-xs text-danger">Backend unavailable. Case registry could not be loaded.</div>}

      <div className="flex items-center gap-1.5 text-[11px]">
        {(["ALL", "OPEN", "IN_REVIEW", "ESCALATED", "SAR_FILED", "CLOSED"] as const).map((s) => (
          <button key={s} onClick={() => setStatus(s)} className={`h-8 px-3 rounded-md mono border ${status === s ? "bg-primary text-primary-foreground border-primary" : "border-border bg-card/60"}`}>{s}</button>
        ))}
      </div>

      <Panel title={`${filtered.length} cases`} dense>
        {isLoading ? (
          <div className="h-40 flex items-center justify-center text-xs text-muted-foreground">Loading cases…</div>
        ) : !filtered.length ? (
          <div className="h-40 flex items-center justify-center text-xs text-muted-foreground">No cases available from backend</div>
        ) : (
        <div className="overflow-auto scrollbar-thin max-h-[calc(100vh-280px)]">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-card/95 backdrop-blur text-[10px] uppercase tracking-wider text-muted-foreground z-10">
              <tr className="text-left border-b border-border">
                {["Case ID", "Pri", "Title", "Linked Alerts", "Officer", "Status", "Created", "SLA", "Escalation"].map((h) => (
                  <th key={h} className="px-2 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} onClick={() => setSelected(c)} className="border-b border-border/50 cursor-pointer hover:bg-accent/30">
                  <td className="px-2 py-1.5 mono text-[11px]">{c.id}</td>
                  <td><PriorityBadge p={c.priority} /></td>
                  <td className="text-xs">{c.title}</td>
                  <td className="text-[11px] text-muted-foreground">{c.linkedAlerts} alerts</td>
                  <td className="text-[11px]">{c.officer}</td>
                  <td><StatusBadge status={c.status} /></td>
                  <td className="mono text-[10px] text-muted-foreground">{new Date(c.createdAt).toLocaleDateString()}</td>
                  <td><SLATimer dueAt={c.slaDueAt} /></td>
                  <td className="mono text-[10px] text-warning">{c.escalation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </Panel>

      {selected && (
        <div className="fixed inset-0 z-50 flex">
          <div className="flex-1 bg-background/60 backdrop-blur-sm" onClick={() => setSelected(null)} />
          <aside className="w-[640px] bg-card border-l border-border overflow-y-auto scrollbar-thin">
            <header className="sticky top-0 z-10 bg-card/95 backdrop-blur border-b border-border px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2"><Briefcase className="h-4 w-4 text-primary" /><div><div className="text-[10px] uppercase tracking-wider text-muted-foreground">Case</div><div className="mono text-sm">{selected.id}</div></div></div>
              <button onClick={() => setSelected(null)} className="h-7 w-7 rounded hover:bg-accent flex items-center justify-center"><X className="h-4 w-4" /></button>
            </header>
            <div className="p-4 space-y-4">
              <div className="text-sm font-medium">{selected.title}</div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <Field label="Officer" value={selected.officer} />
                <Field label="Status" value={<StatusBadge status={selected.status} />} />
                <Field label="Escalation" value={selected.escalation} />
                <Field label="Linked alerts" value={`${selected.linkedAlerts}`} />
                <Field label="Created" value={new Date(selected.createdAt).toLocaleString()} />
                <Field label="SLA" value={<SLATimer dueAt={selected.slaDueAt} />} />
                <Field label="SAR status" value={selected.sarStatus ?? "—"} />
                <Field label="Source alert" value={selected.sourceAlert ?? selected.sourceAlerts?.[0] ?? "—"} />
                <Field label="Case id" value={selected.caseId ?? selected.id} />
              </div>

              <div className="flex gap-2 text-xs">
                <button onClick={handleAssign} className="h-8 px-3 rounded-md border border-border bg-card/60">Assign</button>
                <button onClick={handleFreeze} className="h-8 px-3 rounded-md border border-warning/40 text-warning bg-warning/5 flex items-center gap-1.5"><Snowflake className="h-3 w-3" /> Freeze</button>
                <button onClick={handleSar} className="h-8 px-3 rounded-md border border-primary/40 text-primary bg-primary/10 flex items-center gap-1.5"><CheckCircle2 className="h-3 w-3" /> SAR</button>
              </div>

              <div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Investigation Timeline</div>
                <ol className="relative border-l border-border ml-3 space-y-3 text-xs">
                  {(selected.evidence?.length ? selected.evidence : [selected.status, selected.escalation, selected.officer ?? "unassigned"]).map((entry, i) => (
                    <li key={i} className="ml-3">
                      <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-primary" />
                      <div className="mono text-[10px] text-muted-foreground">Event {i + 1}</div>
                      <div>{String(entry)}</div>
                    </li>
                  ))}
                </ol>
              </div>

              <div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Audit Trail</div>
                <div className="rounded-md border border-border bg-card/40 divide-y divide-border/50 text-[11px]">
                  {[(selected.caseId ?? selected.id), selected.status, selected.escalation, selected.sarStatus ?? "SAR_PENDING"].map((a, idx) => (
                    <div key={`audit-${idx}-${String(a)}`} className="px-3 py-1.5 flex items-center justify-between"><span className="mono text-muted-foreground">{String(a)}</span><FileText className="h-3 w-3 text-muted-foreground" /></div>
                  ))}
                </div>
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="rounded-md border border-border bg-card/40 p-2"><div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div><div className="mt-0.5 mono text-xs">{value}</div></div>;
}
