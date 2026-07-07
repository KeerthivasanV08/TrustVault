import client from './client';
import type { Case } from '@/types';
import { extractCases, normalizeCase } from '@/lib/normalizers/caseNormalizer';

export async function fetchCases(): Promise<Case[]> {
  const raw = await client.request<unknown>({ path: '/api/cases' });
  return extractCases(raw);
}

export async function fetchCase(id: string): Promise<Case> {
  const raw = await client.request<unknown>({ path: `/api/cases/${encodeURIComponent(id)}` });
  return normalizeCase(raw);
}

export async function createCase(payload: Partial<Case>): Promise<Case> {
  const raw = await client.request<unknown>({ method: 'POST', path: '/api/cases/create', body: payload });
  return normalizeCase(raw);
}

export async function assignCase(id: string, officerId: string) {
  return client.request<void>({ method: 'POST', path: `/api/cases/${encodeURIComponent(id)}/assign`, body: { officerId } });
}

export async function freezeCase(id: string) {
  return client.request<void>({ method: 'POST', path: `/api/cases/${encodeURIComponent(id)}/freeze` });
}

export async function sarCase(id: string) {
  return client.request<void>({ method: 'POST', path: `/api/cases/${encodeURIComponent(id)}/sar`, body: { evidence: 'SAR_REQUESTED' } });
}

export function normalizeCase(raw: any): Case {
  const id = String(raw?.id ?? raw?.case_id ?? raw?.caseId ?? '');
  const createdAt = Number(raw?.createdAt ?? raw?.created_at ?? Date.now());
  const slaDueAt = Number(raw?.slaDueAt ?? raw?.sla_due_at ?? createdAt + 2 * 60 * 60_000);
  const linkedAlerts = Number(raw?.linkedAlerts ?? raw?.linked_alerts ?? (Array.isArray(raw?.source_alerts) ? raw.source_alerts.length : 0));
  return {
    id,
    caseId: raw?.case_id ?? raw?.caseId ?? id,
    priority: String(raw?.priority ?? 'P3').toUpperCase() as Case['priority'],
    title: String(raw?.title ?? raw?.reason ?? raw?.summary ?? 'AML investigation case'),
    linkedAlerts,
    officer: raw?.officer ?? raw?.assigned_officer ?? null,
    status: String(raw?.status ?? 'OPEN').toUpperCase(),
    createdAt,
    slaDueAt,
    escalation: raw?.escalation ?? raw?.escalation_level ?? 'L1',
    sourceAlert: raw?.source_alert ?? raw?.sourceAlert,
    sourceAlerts: Array.isArray(raw?.source_alerts) ? raw.source_alerts : raw?.source_alerts ? [String(raw.source_alerts)] : undefined,
    evidence: Array.isArray(raw?.evidence) ? raw.evidence : raw?.evidence ? [raw.evidence] : undefined,
    sarStatus: raw?.sarStatus ?? raw?.sar_status,
  };
}
