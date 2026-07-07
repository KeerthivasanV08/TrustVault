import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Panel } from "@/components/aml/Panel";
import { RiskScoreBadge } from "@/components/aml/Badges";
import type { Account } from '@/types';
import { useAccount, useAccountList } from '@/hooks/useAccounts';
import { Globe, Shield, ShieldAlert, Smartphone, Wifi } from "lucide-react";

export const Route = createFileRoute("/accounts")({
  head: () => ({ meta: [{ title: "Account 360 — TrustVault" }] }),
  component: AccountsPage,
});

function AccountsPage() {
  const [q, setQ] = useState("");
  const [tier, setTier] = useState<"ALL" | Account["riskTier"]>("ALL");
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);

  const listQuery = useAccountList({ limit: 50, search: q || undefined, risk: tier === "ALL" ? undefined : tier, offset: 0 });
  const selectedQuery = useAccount(selectedAccountId ?? undefined);

  const accounts = listQuery.data?.results ?? [];
  const selected = selectedQuery.data;
  const selectedAccount = selected ?? accounts.find((a) => a.id === selectedAccountId);
  const isLoading = listQuery.isLoading;
  const isError = listQuery.isError;

  const placeholderAccounts: Account[] = Array.from({ length: 10 }, (_, idx) => ({
    id: `loading-${idx}`,
    name: "Loading…",
    country: "",
    riskScore: 0,
    sanctionsHit: false,
    pep: false,
    riskTier: "",
  }));

  const list = isLoading ? placeholderAccounts : accounts;

  return (
    <div className="p-4 space-y-3 h-[calc(100vh-120px)] min-h-0 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Account 360 Intelligence</h1>
          <p className="text-xs text-muted-foreground">Unified KYC · device · graph · transaction surface</p>
        </div>
        <div className="flex items-center gap-1.5">
          {(["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"] as const).map((t) => (
            <button key={t} onClick={() => setTier(t)} className={`h-7 px-2.5 mono text-[10px] rounded border ${tier === t ? "bg-primary text-primary-foreground border-primary" : "border-border bg-card/60"}`}>{t}</button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-12 gap-3 flex-1 min-h-0 overflow-hidden">
        <Panel title="Account Directory" className="col-span-4 min-h-0 h-full" dense>
          <div className="flex h-full min-h-0 flex-col">
          <div className="p-2 border-b border-border shrink-0">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search account…" className="w-full h-8 px-3 rounded-md bg-input/60 border border-border text-xs focus:outline-none focus:border-primary" />
          </div>
          <div className="px-3 py-2 border-b border-border text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{isLoading ? 'Loading accounts…' : isError ? 'Failed to load accounts' : `${accounts.length} accounts`}</div>
          <ul className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin divide-y divide-border/50">
            {list.slice(0, 60).map((a) => (
              <li key={a.id} onClick={() => setSelectedAccountId(a.id)} className={`p-2.5 cursor-pointer hover:bg-accent/30 ${selected?.id === a.id ? "bg-accent/40" : ""}`}>
                <div className="flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="text-xs font-medium whitespace-normal break-words leading-relaxed">{a.name}</div>
                    <div className="mono text-[10px] text-muted-foreground whitespace-normal break-words">{a.id} · {a.country}</div>
                  </div>
                  <RiskScoreBadge score={a.riskScore ?? 0} />
                </div>
                <div className="mt-1 flex gap-1">
                  {a.sanctionsHit && <span className="text-[9px] mono px-1 py-0.5 rounded bg-critical/10 text-critical border border-critical/40">SANCTIONS</span>}
                  {a.pep && <span className="text-[9px] mono px-1 py-0.5 rounded bg-warning/10 text-warning border border-warning/40">PEP</span>}
                  <span className="text-[9px] mono px-1 py-0.5 rounded bg-muted text-muted-foreground border border-border">{a.riskTier}</span>
                </div>
              </li>
            ))}
          </ul>
          </div>
        </Panel>

        {selectedAccount && (
          <div className="col-span-8 min-h-0 overflow-hidden">
            <div className="h-full min-h-0 overflow-y-auto overflow-x-hidden pr-1 scrollbar-thin">
              <div className="grid grid-cols-2 gap-3 min-h-0 pb-1">
                <section className="col-span-2 rounded-lg border border-border bg-card/60 overflow-hidden flex flex-col">
                  <div className="px-3 py-2 border-b border-border">
                    <div className="text-[11px] uppercase tracking-[0.18em] font-medium whitespace-normal break-words leading-relaxed text-warning">Profile Summary</div>
                  </div>
                  <div className="p-3 space-y-4 text-xs">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                      <div className="min-w-0">
                        <div className="text-base font-semibold whitespace-normal break-words leading-relaxed">{selectedAccount.name ?? selectedAccount.id}</div>
                        <div className="mono text-[10px] text-muted-foreground uppercase tracking-[0.18em] whitespace-normal break-words">{selectedAccount.id}</div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <RiskScoreBadge score={selectedAccount.riskScore ?? 0} />
                        <span className="text-[10px] mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">{safeValue(selectedAccount.risk_level ?? selectedAccount.riskTier)}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <StatRow label="KYC Status" value={selectedAccount.kyc_status} />
                      <StatRow label="KYC City" value={selectedAccount.kyc_city} />
                      <StatRow label="Created At" value={formatDate(selectedAccount.created_at ?? selectedAccount.createdAt)} />
                      <StatRow label="Risk Score" value={formatScore(deriveOnboardingRisk(selectedAccount))} />
                      <StatRow label="Risk Level" value={safeValue(selectedAccount.risk_level ?? selectedAccount.riskTier)} />
                      <StatRow label="Decision" value={selectedAccount.decision} />
                      <StatRow label="Confidence" value={formatScore(selectedAccount.confidence)} />
                    </div>
                  </div>
                </section>

                <section className="rounded-lg border border-border bg-card/60 overflow-hidden flex flex-col min-h-0">
                  <div className="px-3 py-2 border-b border-border">
                    <div className="text-[11px] uppercase tracking-[0.18em] font-medium whitespace-normal break-words leading-relaxed text-warning">Device Intelligence</div>
                  </div>
                  <div className="p-3 grid grid-cols-1 gap-3 text-xs">
                    <StatRow label="Device ID" value={selectedAccount.device_id} />
                    <StatRow label="Device Model" value={selectedAccount.device_model_name} />
                    <StatRow label="Device Year" value={selectedAccount.device_year} />
                    <StatRow label="Device Age Years" value={selectedAccount.device_age_years} />
                    <StatRow label="Device Age Days" value={selectedAccount.device_age_days} />
                    <StatRow label="Device Trust Score" value={formatScore(selectedAccount.device_trust_score)} />
                    <StatRow label="Device Shared Count" value={selectedAccount.device_shared_count} />
                    <StatRow label="Root Status" value={formatBoolean(selectedAccount.root_status)} />
                    <StatRow label="Emulator Flag" value={formatBoolean(selectedAccount.emulator_flag)} />
                    <StatRow label="App Cloner Flag" value={formatBoolean(selectedAccount.app_cloner_flag)} />
                    <StatRow label="Biometric Enabled" value={formatBoolean(selectedAccount.biometric_enabled)} />
                  </div>
                </section>

                <section className="rounded-lg border border-border bg-card/60 overflow-hidden flex flex-col min-h-0">
                  <div className="px-3 py-2 border-b border-border">
                    <div className="text-[11px] uppercase tracking-[0.18em] font-medium whitespace-normal break-words leading-relaxed text-warning">SIM Intelligence</div>
                  </div>
                  <div className="p-3 grid grid-cols-1 gap-3 text-xs">
                    <StatRow label="Registered IMSI" value={selectedAccount.registered_imsi} />
                    <StatRow label="Current IMSI" value={selectedAccount.current_imsi} />
                    <StatRow label="SIM Present" value={formatBoolean(selectedAccount.sim_present)} />
                    <StatRow label="SIM Slot Count" value={selectedAccount.sim_slot_count} />
                    <StatRow label="SIM Binding OK" value={formatBoolean(selectedAccount.sim_binding_ok)} />
                    <StatRow label="SIM Swap Flag" value={formatBoolean(selectedAccount.sim_swap_flag)} />
                    <StatRow label="SIM Age Days" value={selectedAccount.sim_age_days} />
                    <StatRow label="Multi SIM Flag" value={formatBoolean(selectedAccount.multi_sim_flag)} />
                  </div>
                </section>

                <section className="rounded-lg border border-border bg-card/60 overflow-hidden flex flex-col min-h-0">
                  <div className="px-3 py-2 border-b border-border">
                    <div className="text-[11px] uppercase tracking-[0.18em] font-medium whitespace-normal break-words leading-relaxed text-warning">Network / IP Intelligence</div>
                  </div>
                  <div className="p-3 grid grid-cols-1 gap-3 text-xs">
                    <StatRow label="IP Address" value={selectedAccount.ip_address} />
                    <StatRow label="ISP Name" value={selectedAccount.isp_name} />
                    <StatRow label="VPN Detected" value={formatBoolean(selectedAccount.vpn_detected)} />
                    <StatRow label="VPN Flag" value={formatBoolean(selectedAccount.vpn_flag)} />
                    <StatRow label="IP Risk Score" value={formatScore(selectedAccount.ip_risk_score)} />
                  </div>
                </section>

                <section className="rounded-lg border border-border bg-card/60 overflow-hidden flex flex-col min-h-0">
                  <div className="px-3 py-2 border-b border-border">
                    <div className="text-[11px] uppercase tracking-[0.18em] font-medium whitespace-normal break-words leading-relaxed text-warning">KYC / Identity Intelligence</div>
                  </div>
                  <div className="p-3 grid grid-cols-1 gap-3 text-xs">
                    <StatRow label="Identity Trust Score" value={formatScore(selectedAccount.identity_trust_score)} />
                    <StatRow label="Face Match Score" value={formatScore(selectedAccount.face_match_score)} />
                    <StatRow label="Sanction Hit" value={formatBoolean(selectedAccount.sanction_hit)} />
                    <StatRow label="PEP Hit" value={formatBoolean(selectedAccount.pep_hit)} />
                    <StatRow label="Requires Review" value={formatBoolean(selectedAccount.requires_review)} />
                    <StatRow label="Requires Block" value={formatBoolean(selectedAccount.requires_block)} />
                    <StatRow label="Requires EDD" value={formatBoolean(selectedAccount.requires_edd)} />
                    <StatRow label="Officer Recommendation" value={selectedAccount.officer_recommendation} />
                  </div>
                </section>

                <section className="rounded-lg border border-border bg-card/60 overflow-hidden flex flex-col min-h-0">
                  <div className="px-3 py-2 border-b border-border">
                    <div className="text-[11px] uppercase tracking-[0.18em] font-medium whitespace-normal break-words leading-relaxed text-warning">Behavioral Onboarding Signals</div>
                  </div>
                  <div className="p-3 grid grid-cols-1 gap-3 text-xs">
                    <StatRow label="Typing Speed" value={formatScore(selectedAccount.typing_speed)} />
                    <StatRow label="Form Completion Time" value={formatScore(selectedAccount.form_completion_time)} />
                    <StatRow label="Onboarding Speed MS" value={selectedAccount.onboarding_speed_ms} />
                    <StatRow label="Copy Paste Ratio" value={formatScore(selectedAccount.copy_paste_ratio)} />
                    <StatRow label="OTP Retry Count" value={selectedAccount.otp_retry_count} />
                  </div>
                </section>

                <section className="col-span-2 rounded-lg border border-border bg-card/60 overflow-hidden flex flex-col min-h-0">
                  <div className="px-3 py-2 border-b border-border">
                    <div className="text-[11px] uppercase tracking-[0.18em] font-medium whitespace-normal break-words leading-relaxed text-warning">Onboarding Explainability</div>
                  </div>
                  <div className="p-3 text-xs space-y-2 break-words leading-relaxed">
                    {buildExplainability(selectedAccount).map((reason, index) => (
                      <div key={index} className="rounded-md border border-border/50 bg-card/80 p-2 break-words">
                        <div className="font-medium text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Signal</div>
                        <div className="mt-1 whitespace-normal break-words leading-relaxed">{reason}</div>
                      </div>
                    ))}
                    {buildExplainability(selectedAccount).length === 0 && (
                      <div className="rounded-md border border-border/50 bg-card/80 p-3 text-muted-foreground">No major onboarding risk indicators detected.</div>
                    )}
                  </div>
                </section>

                <section className="col-span-2 rounded-lg border border-border bg-card/60 overflow-hidden flex flex-col min-h-0">
                  <div className="px-3 py-2 border-b border-border">
                    <div className="text-[11px] uppercase tracking-[0.18em] font-medium whitespace-normal break-words text-warning">Suspicious Relationships</div>
                  </div>
                  <div className="p-3 text-xs min-h-0">
                    {Array.isArray(selectedAccount.suspicious_relationships) && selectedAccount.suspicious_relationships.length > 0 ? (
                      <ul className="space-y-2">
                        {selectedAccount.suspicious_relationships.map((relationship, idx) => (
                          <li key={idx} className="rounded-md border border-border/50 bg-card/80 p-2 break-words">
                            {renderRelationship(relationship)}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div className="rounded-md border border-border/50 bg-card/80 p-3 text-muted-foreground">No suspicious account relationships available from account CSV data.</div>
                    )}
                  </div>
                </section>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function safeValue(value: unknown): string {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "number") return Number.isFinite(value) ? value.toString() : "N/A";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed || trimmed.toLowerCase() === "nan") return "N/A";
    return trimmed;
  }
  return String(value);
}

function formatBoolean(value: unknown): string {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return value === 1 ? "Yes" : value === 0 ? "No" : "N/A";
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "true" || normalized === "1") return "Yes";
    if (normalized === "false" || normalized === "0") return "No";
  }
  return "N/A";
}

function formatScore(value: unknown): string {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "N/A";
    return Math.round(value).toString();
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return "N/A";
    return Math.round(parsed).toString();
  }
  return "N/A";
}

function formatDate(value: unknown): string {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "number") {
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? "N/A" : d.toLocaleDateString();
  }
  if (typeof value === "string") {
    const parsed = Date.parse(value);
    if (Number.isNaN(parsed)) return "N/A";
    return new Date(parsed).toLocaleDateString();
  }
  return "N/A";
}

function deriveOnboardingRisk(account: Account): number | undefined {
  if (account.onboarding_risk_score != null && Number.isFinite(account.onboarding_risk_score)) {
    return account.onboarding_risk_score;
  }
  if (account.final_risk_score != null && Number.isFinite(account.final_risk_score)) {
    return account.final_risk_score;
  }
  if (account.identity_trust_score != null && Number.isFinite(account.identity_trust_score)) {
    return Math.round(Math.max(0, Math.min(100, 100 - account.identity_trust_score)));
  }
  return undefined;
}

function deriveSimRisk(account: Account): number | undefined {
  let score = 0;
  if (account.sim_swap_flag === 1 || account.sim_swap_flag === true) score += 50;
  if (account.sim_binding_ok === 0 || account.sim_binding_ok === false) score += 30;
  if (account.multi_sim_flag === 1 || account.multi_sim_flag === true) score += 20;
  if (account.sim_age_days != null && Number.isFinite(account.sim_age_days) && account.sim_age_days > 180) score = Math.max(score - 10, 0);
  return score > 0 ? Math.min(score, 100) : undefined;
}

function deriveVpnRisk(account: Account): number | undefined {
  let score = 0;
  if (account.vpn_flag === 1 || account.vpn_flag === true) score += 50;
  if (account.vpn_detected === true) score += 30;
  if (account.ip_risk_score != null && Number.isFinite(account.ip_risk_score)) score += Math.min(50, Math.max(0, Math.round(account.ip_risk_score)));
  return score > 0 ? Math.min(score, 100) : undefined;
}

function deriveGraphProximity(account: Account): number | undefined {
  if (account.graph_score != null && Number.isFinite(account.graph_score)) return account.graph_score;
  if (account.graphProximity != null && Number.isFinite(account.graphProximity)) return account.graphProximity;
  return undefined;
}

function deriveSuspiciousRisk(account: Account): number | undefined {
  let score = 0;
  if (account.requires_review) score += 20;
  if (account.requires_block) score += 30;
  if (account.sanction_hit === 1) score += 30;
  if (account.pep_hit === 1) score += 20;
  if (account.device_shared_count != null && account.device_shared_count > 3) score += 10;
  if (account.copy_paste_ratio != null && account.copy_paste_ratio > 0.8) score += 10;
  if (account.otp_retry_count != null && account.otp_retry_count >= 3) score += 10;
  return score > 0 ? Math.min(score, 100) : undefined;
}

function buildExplainability(account: Account): string[] {
  const reasons: string[] = [];
  if (account.sanction_hit === 1) reasons.push("Sanction screening hit detected");
  if (account.pep_hit === 1) reasons.push("PEP escalation required");
  if (account.device_shared_count != null && account.device_shared_count > 3) reasons.push("Device reused across multiple onboarding accounts");
  if (account.sim_swap_flag === 1 || account.sim_swap_flag === true) reasons.push("SIM swap risk detected");
  if (account.sim_binding_ok === 0 || account.sim_binding_ok === false) reasons.push("SIM binding mismatch detected");
  if (account.vpn_flag === 1 || account.vpn_flag === true || account.vpn_detected === true) reasons.push("VPN detected during onboarding");
  if (account.face_match_score != null && Number.isFinite(account.face_match_score) && account.face_match_score < 0.8) reasons.push("Low face match score detected during onboarding");
  if (account.otp_retry_count != null && account.otp_retry_count >= 3) reasons.push("Multiple OTP retries observed");
  if (account.emulator_flag === 1 || account.emulator_flag === true) reasons.push("Emulator environment detected");
  if (account.root_status === 1 || account.root_status === true) reasons.push("Rooted device detected");
  if (account.app_cloner_flag === 1 || account.app_cloner_flag === true) reasons.push("App cloner detected");
  if (account.ip_risk_score != null && Number.isFinite(account.ip_risk_score) && account.ip_risk_score > 60) reasons.push("High-risk IP reputation");
  if (account.multi_sim_flag === 1 || account.multi_sim_flag === true) reasons.push("Multiple SIM usage detected");
  return reasons;
}

function renderRelationship(item: unknown): string {
  if (item == null) return "Unknown relationship";
  if (typeof item === "string") return item;
  if (typeof item === "object") {
    const obj = item as Record<string, unknown>;
    if (obj.user_id) return String(obj.user_id);
    if (obj.id) return String(obj.id);
    if (obj.name) return String(obj.name);
    return JSON.stringify(obj);
  }
  return String(item);
}

function StatRow({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-md border border-border/50 bg-card/80 p-2 min-w-0">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground whitespace-normal break-words leading-relaxed">{label}</div>
      <div className="mt-1 mono text-sm whitespace-normal break-words leading-relaxed">{safeValue(value)}</div>
    </div>
  );
}

function Bar({ label, value, icon: Icon, invert = false }: { label: string; value?: number; icon: any; invert?: boolean }) {
  const safe = value != null && Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : undefined;
  const tone = safe == null ? "bg-muted" : safe > 75 ? "bg-critical" : safe > 50 ? "bg-warning" : safe > 25 ? "bg-info" : "bg-success";
  return (
    <div className="rounded-md border border-border bg-card/40 p-2 min-w-0">
      <div className="flex items-start justify-between gap-2 min-w-0">
        <div className="flex items-center gap-1.5 text-muted-foreground min-w-0"><Icon className="h-3 w-3 shrink-0" /><span className="text-[10px] uppercase tracking-wider whitespace-normal break-words leading-relaxed">{label}</span></div>
        <span className="mono text-xs shrink-0">{safe != null ? safe : "N/A"}</span>
      </div>
      <div className="mt-1.5 h-1 bg-muted rounded overflow-hidden"><div className={`h-full ${tone}`} style={{ width: `${safe ?? 0}%` }} /></div>
    </div>
  );
}
