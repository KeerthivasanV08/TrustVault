import { createFileRoute } from "@tanstack/react-router";
import { Panel, StatCard } from "@/components/aml/Panel";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download, FileSignature, FileText, FileSpreadsheet } from "lucide-react";
import { useMemo } from "react";
import { toast } from 'sonner';
import { useAlerts } from '@/hooks/useAlerts';
import { useCases } from '@/hooks/useCases';
import { useExportReport, useHighRiskReports, useManualReviewReports, useReports, useSarReports, useStrReports } from '@/hooks/useReports';

export const Route = createFileRoute("/reports")({
  head: () => ({ meta: [{ title: "Reports — TrustVault" }] }),
  component: ReportsPage,
});

function ReportsPage() {
  const reportsQ = useReports();
  const sarQ = useSarReports();
  const strQ = useStrReports();
  const highRiskQ = useHighRiskReports();
  const manualReviewQ = useManualReviewReports();
  const exportReport = useExportReport();
  const alertsQ = useAlerts();
  const casesQ = useCases();

  const reportList = reportsQ.data ?? [];
  const alertList = alertsQ.data ?? [];
  const alertEscalations = alertsQ.escalations ?? [];
  const caseList = casesQ.data ?? [];
  const workloadLoading = reportsQ.isLoading || casesQ.isLoading || alertsQ.isLoading;
  const riskLoading = sarQ.isLoading || strQ.isLoading || highRiskQ.isLoading || manualReviewQ.isLoading;
  const pdfSupported = false;

  const handleExport = async (format: 'json' | 'csv' | 'pdf') => {
    if (format === 'pdf' && !pdfSupported) {
      toast.error('PDF export not available from backend');
      return;
    }

    try {
      const payload = await exportReport.mutateAsync(format);
      const data = typeof payload === 'string' ? payload : JSON.stringify(payload);
      const mimeType = format === 'csv' ? 'text/csv' : 'application/json';
      const blob = new Blob([data], { type: mimeType });
      const name = `reports.${format === 'json' ? 'json' : format === 'csv' ? 'csv' : 'json'}`;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = name;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
      toast.success(`Downloaded ${name}`);
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const officerWorkload = useMemo(() => {
    const workload = new Map<string, { officer: string; open: number; closed: number; sar: number }>();
    const add = (officer: string, open = 0, closed = 0, sar = 0) => {
      const key = officer || 'Unassigned';
      const current = workload.get(key) ?? { officer: key, open: 0, closed: 0, sar: 0 };
      workload.set(key, { officer: key, open: current.open + open, closed: current.closed + closed, sar: current.sar + sar });
    };

    if (caseList.length) {
      for (const c of caseList) {
        const officer = c.officer ?? 'Unassigned';
        if (c.status === 'CLOSED') add(officer, 0, 1, 0);
        else if (c.status === 'SAR_FILED') add(officer, 0, 0, 1);
        else add(officer, 1, 0, 0);
      }
    } else if (alertList.length) {
      for (const alert of alertList) {
        const officer = alert.assignedOfficer ?? 'Unassigned';
        if (alert.status === 'CLOSED') add(officer, 0, 1, 0);
        else add(officer, 1, 0, 0);
      }
    } else {
      for (const report of reportList) {
        const officer = report.officerRecommendation ?? report.sourceEngine ?? report.reportType ?? 'System';
        if (report.reportType === 'SAR') add(officer, 0, 0, 1);
        else if (report.reviewStatus === 'CLOSED') add(officer, 0, 1, 0);
        else add(officer, 1, 0, 0);
      }
    }

    return Array.from(workload.values()).slice(0, 8);
  }, [caseList, alertList, reportList]);

  const riskDistribution = useMemo(() => {
    const buckets = [
      { name: 'SAR', value: sarQ.data?.length ?? 0, color: 'oklch(0.62 0.24 22)' },
      { name: 'STR', value: strQ.data?.length ?? 0, color: 'oklch(0.78 0.17 75)' },
      { name: 'High risk', value: highRiskQ.data?.length ?? 0, color: 'oklch(0.7 0.18 240)' },
      { name: 'Manual review', value: manualReviewQ.data?.length ?? 0, color: 'oklch(0.72 0.17 160)' },
    ];
    const total = buckets.reduce((sum, bucket) => sum + bucket.value, 0) || 1;
    return buckets.map((bucket) => ({ ...bucket, pct: Math.round((bucket.value / total) * 100) }));
  }, [sarQ.data?.length, strQ.data?.length, highRiskQ.data?.length, manualReviewQ.data?.length]);

  const auditRows = useMemo(() => [...reportList].sort((a, b) => (b.timestamp ?? 0) - (a.timestamp ?? 0)).slice(0, 24), [reportList]);

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Reports & Audit Center</h1>
          <p className="text-xs text-muted-foreground">Regulatory reporting · SAR / STR workflows · 30-day audit log</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('json')}
            disabled={exportReport.isLoading}
            className="h-8 px-3 rounded-md border border-border bg-card/60 text-xs flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          ><Download className="h-3.5 w-3.5" /> JSON</button>
          <button
            onClick={() => handleExport('csv')}
            disabled={exportReport.isLoading}
            className="h-8 px-3 rounded-md border border-border bg-card/60 text-xs flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          ><FileSpreadsheet className="h-3.5 w-3.5" /> CSV</button>
          <button
            onClick={() => handleExport('pdf')}
            disabled={!pdfSupported}
            title={!pdfSupported ? 'PDF export not available from backend' : undefined}
            className="h-8 px-3 rounded-md border border-border bg-card/60 text-xs flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          ><FileText className="h-3.5 w-3.5" /> PDF</button>
        </div>
        <div className="space-y-1">
          {!pdfSupported && <div className="text-[10px] text-muted-foreground">PDF export not available from backend</div>}
          {alertEscalations.length > 0 && <div className="text-[10px] text-muted-foreground">{alertEscalations.length} alert escalations loaded</div>}
        </div>
      </div>

      {(reportsQ.isError || sarQ.isError || strQ.isError || highRiskQ.isError || manualReviewQ.isError) && (
        <div className="rounded-md border border-danger/40 bg-danger/5 px-3 py-2 text-xs text-danger">
          Backend unavailable. Reports could not be fully loaded.
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="SAR filed (30d)" value={sarQ.data?.length ?? 0} tone="primary" icon={<FileSignature className="h-3.5 w-3.5" />} trend={{ dir: "up", value: "live" }} />
        <StatCard label="STR filed (30d)" value={strQ.data?.length ?? 0} tone="warning" />
        <StatCard label="High risk" value={highRiskQ.data?.length ?? 0} tone="success" />
        <StatCard label="Manual review" value={manualReviewQ.data?.length ?? 0} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Panel title="Officer Workload" className="h-72 lg:col-span-2">
          {workloadLoading ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">Loading workload…</div>
          ) : !officerWorkload.length ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No report workload data available</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={officerWorkload} margin={{ top: 10, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="var(--color-border)" strokeDasharray="2 4" />
                <XAxis dataKey="officer" tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} />
                <YAxis tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", fontSize: 11 }} />
                <Bar dataKey="open" fill="oklch(0.78 0.17 75)" />
                <Bar dataKey="closed" fill="oklch(0.72 0.17 160)" />
                <Bar dataKey="sar" fill="oklch(0.7 0.18 240)" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>
        <Panel title="Risk Category Breakdown" className="h-72">
          {reportsQ.isLoading ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">Loading distribution…</div>
          ) : !riskDistribution.some((bucket) => bucket.value > 0) ? (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No report distribution data available</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={riskDistribution.filter((bucket) => bucket.value > 0)} dataKey="value" nameKey="name" innerRadius={40} outerRadius={75}>
                  {riskDistribution.filter((bucket) => bucket.value > 0).map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      <Panel title="Audit Log · last 30 days" dense>
        {reportsQ.isLoading ? (
          <div className="h-40 flex items-center justify-center text-xs text-muted-foreground">Loading audit log…</div>
        ) : !auditRows.length ? (
          <div className="h-40 flex items-center justify-center text-xs text-muted-foreground">No audit records available from backend</div>
        ) : (
        <div className="overflow-auto scrollbar-thin max-h-[calc(100vh-560px)]">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-card/95 backdrop-blur text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr className="text-left border-b border-border">
                {["Timestamp", "Action", "Officer", "Target", "Status"].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {auditRows.map((a, i) => (
                <tr key={i} className="border-b border-border/50 hover:bg-accent/30">
                  <td className="px-3 py-1.5 mono text-[10px] text-muted-foreground">{new Date(a.timestamp ?? Date.now()).toISOString()}</td>
                  <td className="mono text-[11px]">{a.reportType}</td>
                  <td>{a.officerRecommendation ?? a.sourceEngine ?? "system"}</td>
                  <td className="mono text-[11px]">{a.transactionId ?? a.userId ?? a.reportId ?? a.id}</td>
                  <td><span className="text-[10px] mono px-1.5 py-0.5 rounded border border-border text-muted-foreground">{a.reviewStatus ?? a.escalationLevel ?? "OPEN"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </Panel>
    </div>
  );
}
