import type { Case } from '@/types';
import { extractList } from './util';

export function normalizeCase(raw: any): Case {
  const id = String(raw?.id ?? raw?.case_id ?? raw?.caseId ?? '');
  const createdAt = Number(raw?.createdAt ?? raw?.created_at ?? Date.now());
  const slaDueAt = Number(raw?.slaDueAt ?? raw?.sla_due_at ?? createdAt + 2 * 60 * 60_000);
  return {
    id,
    caseId: raw?.case_id ?? raw?.caseId ?? id,
    priority: String(raw?.priority ?? 'P3').toUpperCase() as Case['priority'],
    title: String(raw?.title ?? raw?.reason ?? raw?.summary ?? 'AML investigation case'),
    linkedAlerts: Number(raw?.linkedAlerts ?? raw?.linked_alerts ?? (Array.isArray(raw?.source_alerts) ? raw.source_alerts.length : 0)),
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

export function extractCases(raw: unknown): Case[] {
  const items = extractList<Case>(raw).map(normalizeCase);
  // Deduplicate by case ID - keep latest (last in array)
  const seen = new Set<string>();
  return items.reverse().filter((c) => {
    if (seen.has(c.id)) return false;
    seen.add(c.id);
    return true;
  }).reverse();
}
