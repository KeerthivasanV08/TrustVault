import type { Alert } from '@/types';
import { extractList } from './util';

function normalizeDate(value: unknown): number {
  if (value == null || value === '') {
    return Date.now();
  }

  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }

  const asString = String(value).trim();
  if (!asString) {
    return Date.now();
  }

  const numeric = Number(asString);
  if (Number.isFinite(numeric)) {
    return numeric;
  }

  const parsed = Date.parse(asString);
  return Number.isNaN(parsed) ? Date.now() : parsed;
}

export function normalizeAlert(raw: any): Alert {
  const id = String(raw?.id ?? raw?.alert_id ?? raw?.alertId ?? '');
  const createdAt = normalizeDate(raw?.createdAt ?? raw?.created_at ?? raw?.timestamp);
  const slaDueAt = normalizeDate(raw?.slaDueAt ?? raw?.sla_due_at ?? raw?.due_at ?? raw?.deadline_at ?? (createdAt + 2 * 60 * 60_000));
  return {
    id,
    alertId: raw?.alert_id ?? raw?.alertId ?? id,
    priority: String(raw?.priority ?? 'P3').toUpperCase() as Alert['priority'],
    type: String(raw?.type ?? raw?.alert_type ?? 'AML_ALERT'),
    userId: String(raw?.userId ?? raw?.user_id ?? raw?.sender_id ?? raw?.account_id ?? ''),
    userName: raw?.userName ?? raw?.user_name ?? raw?.account_name,
    riskScore: Number(raw?.riskScore ?? raw?.risk_score ?? raw?.final_score ?? 0),
    finalScore: Number(raw?.finalScore ?? raw?.final_score ?? raw?.riskScore ?? raw?.risk_score ?? 0),
    behaviorScore: raw?.behaviorScore ?? raw?.behavioral_score ?? raw?.behavioralScore ? Number(raw?.behaviorScore ?? raw?.behavioral_score ?? raw?.behavioralScore) : undefined,
    sequenceScore: raw?.sequenceScore ?? raw?.sequence_score ? Number(raw?.sequenceScore ?? raw?.sequence_score) : undefined,
    graphScore: raw?.graphScore ?? raw?.graph_score ? Number(raw?.graphScore ?? raw?.graph_score) : undefined,
    reasons: extractList<string>(raw?.reasons ?? raw?.reason_list ?? raw?.reason ?? raw?.signals ?? []),
    evidence: extractList<string>(raw?.evidence ?? raw?.evidence_items ?? raw?.evidence_list ?? []),
    queue: raw?.queue ?? raw?.queue_name ?? raw?.assigned_queue,
    assignedOfficer: raw?.assignedOfficer ?? raw?.assigned_officer_name ?? raw?.assigned_officer ?? null,
    assignedOfficerId: raw?.assigned_officer_id ?? raw?.assignedOfficerId ?? null,
    assignedOfficerName: raw?.assigned_officer_name ?? raw?.assignedOfficerName ?? raw?.assigned_officer ?? null,
    slaDueAt,
    remainingSeconds: raw?.remainingSeconds ?? raw?.remaining_seconds ?? undefined,
    slaBreached: raw?.slaBreached ?? raw?.sla_breached ?? undefined,
    createdAt,
    status: String(raw?.status ?? raw?.state ?? 'OPEN').toUpperCase() as Alert['status'],
    caseId: raw?.caseId ?? raw?.case_id ?? null,
    signals: extractList<string>(raw?.signals ?? raw?.signal_list ?? raw?.signal ?? []),
    amount: raw?.amount != null ? Number(raw.amount) : undefined,
    channel: raw?.channel ? String(raw.channel) : undefined,
    summary: raw?.summary ?? raw?.reason ?? raw?.description,
  };
}

export function extractAlerts(raw: unknown): Alert[] {
  return extractList<Alert>(raw).map(normalizeAlert);
}
