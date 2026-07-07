import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Panel } from "@/components/aml/Panel";
import { Bell, ShieldCheck, Sliders, Zap } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings — TrustVault" }] }),
  component: SettingsPage,
});

function SettingsPage() {
  const [t1, setT1] = useState(70);
  const [t2, setT2] = useState(85);
  const [autoEsc, setAutoEsc] = useState(true);
  const [realtime, setRealtime] = useState(true);
  const [sound, setSound] = useState(false);
  const [dark, setDark] = useState(true);
  const [queue, setQueue] = useState("FIFO");

  return (
    <div className="p-4 space-y-3 max-w-5xl">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Settings</h1>
        <p className="text-xs text-muted-foreground">Console preferences · risk thresholds · queue behavior</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Risk Thresholds" subtitle="Decisioning model bands">
          <div className="space-y-4 text-xs">
            <Slider label="Review threshold" value={t1} onChange={setT1} hint="Scores ≥ value trigger REVIEW queue routing" />
            <Slider label="Block threshold" value={t2} onChange={setT2} hint="Scores ≥ value hard-block + P1 escalation" />
            <div className="rounded-md border border-warning/30 bg-warning/5 p-2.5 text-warning text-[11px] flex items-start gap-2">
              <Sliders className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span>Threshold changes apply to scoring engine v3.7 with 5min propagation.</span>
            </div>
          </div>
        </Panel>

        <Panel title="Auto-Escalation" subtitle="Routing & SLA behavior">
          <div className="space-y-3 text-xs">
            <Toggle label="Auto-escalate on SLA breach" value={autoEsc} onChange={setAutoEsc} />
            <Toggle label="Auto-create case from P1 alert" value={true} onChange={() => {}} />
            <Toggle label="Auto-assign to least-loaded officer" value={true} onChange={() => {}} />
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Queue ordering</div>
              <div className="flex gap-1">
                {["FIFO", "RISK_DESC", "SLA_ASC"].map((q) => (
                  <button key={q} onClick={() => setQueue(q)} className={`h-8 px-3 mono text-[11px] rounded border ${queue === q ? "bg-primary text-primary-foreground border-primary" : "border-border"}`}>{q}</button>
                ))}
              </div>
            </div>
          </div>
        </Panel>

        <Panel title="Realtime Preferences">
          <div className="space-y-3 text-xs">
            <Toggle label="Stream live transactions" value={realtime} onChange={setRealtime} />
            <Toggle label="Sound on P1 alerts" value={sound} onChange={setSound} />
            <Toggle label="Animated graph propagation" value={true} onChange={() => {}} />
            <Toggle label="Compact density mode" value={false} onChange={() => {}} />
          </div>
        </Panel>

        <Panel title="Notifications">
          <div className="space-y-3 text-xs">
            <Toggle label="Desktop notifications" value={true} onChange={() => {}} />
            <Toggle label="Email digest (daily)" value={true} onChange={() => {}} />
            <Toggle label="Slack #aml-warroom" value={false} onChange={() => {}} />
            <Toggle label="PagerDuty on SLA breach" value={true} onChange={() => {}} />
          </div>
        </Panel>

        <Panel title="Appearance">
          <div className="space-y-3 text-xs">
            <Toggle label="Dark mode (recommended)" value={dark} onChange={setDark} />
            <Toggle label="High-contrast borders" value={false} onChange={() => {}} />
            <Toggle label="Reduced motion" value={false} onChange={() => {}} />
          </div>
        </Panel>

        <Panel title="Session">
          <div className="space-y-3 text-xs">
            <Row k="Officer" v="A. Khan · L2 Analyst" />
            <Row k="Role" v="aml.investigator + sar.author" />
            <Row k="Session id" v="sess-7ac1f29b" />
            <Row k="Last login" v={new Date().toUTCString()} />
            <button onClick={() => toast("Settings saved")} className="w-full h-9 rounded-md bg-primary text-primary-foreground text-sm font-medium">Save Settings</button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center justify-between cursor-pointer">
      <span>{label}</span>
      <button onClick={() => onChange(!value)} className={`relative h-5 w-9 rounded-full transition-colors ${value ? "bg-primary" : "bg-muted"}`}>
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-background transition-transform ${value ? "translate-x-4" : "translate-x-0.5"}`} />
      </button>
    </label>
  );
}
function Slider({ label, value, onChange, hint }: any) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span>{label}</span>
        <span className="mono">{value}</span>
      </div>
      <input type="range" min={0} max={100} value={value} onChange={(e) => onChange(+e.target.value)} className="w-full accent-primary" />
      {hint && <div className="text-[10px] text-muted-foreground mt-1">{hint}</div>}
    </div>
  );
}
function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between"><span className="text-muted-foreground">{k}</span><span className="mono">{v}</span></div>;
}
