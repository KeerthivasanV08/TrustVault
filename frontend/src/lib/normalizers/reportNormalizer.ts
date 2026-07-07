import type { Report } from '@/types';
import { extractList } from './util';

export function normalizeReport(raw: any): Report {
  const id = String(raw?.id ?? raw?.report_id ?? raw?.reportId ?? `${raw?.report_type ?? 'REPORT'}-${raw?.timestamp ?? Date.now()}`);
  const timestamp = Number(raw?.timestamp ?? raw?.created_at ?? raw?.createdAt ?? Date.now());
  return {
    id,
    reportId: raw?.report_id ?? raw?.reportId ?? id,
    reportType: String(raw?.report_type ?? raw?.reportType ?? 'MANUAL_REVIEW_ESCALATION'),
    userId: raw?.user_id ?? raw?.userId,
    transactionId: raw?.transaction_id ?? raw?.transactionId,
    decision: raw?.decision,
    finalScore: raw?.final_score != null ? Number(raw.final_score) : raw?.finalScore != null ? Number(raw.finalScore) : undefined,
    behaviorScore: raw?.behavior_score != null ? Number(raw.behavior_score) : raw?.behaviorScore != null ? Number(raw.behaviorScore) : undefined,
    sequenceScore: raw?.sequence_score != null ? Number(raw.sequence_score) : raw?.sequenceScore != null ? Number(raw.sequenceScore) : undefined,
    graphScore: raw?.graph_score != null ? Number(raw.graph_score) : raw?.graphScore != null ? Number(raw.graphScore) : undefined,
    ruleScore: raw?.rule_score != null ? Number(raw.rule_score) : raw?.ruleScore != null ? Number(raw.ruleScore) : undefined,
    officerRecommendation: raw?.officer_recommendation ?? raw?.officerRecommendation,
    immediateAction: raw?.immediate_action ?? raw?.immediateAction,
    reason: raw?.reason,
    reasons: Array.isArray(raw?.reasons) ? raw.reasons : raw?.reasons ? [String(raw.reasons)] : undefined,
    amount: raw?.amount != null ? Number(raw.amount) : undefined,
    sourceEngine: raw?.source_engine ?? raw?.sourceEngine,
    escalationLevel: raw?.escalation_level ?? raw?.escalationLevel,
    reviewStatus: raw?.review_status ?? raw?.reviewStatus,
    evidence: Array.isArray(raw?.evidence) ? raw.evidence : raw?.evidence ? [raw.evidence] : undefined,
    metadata: raw?.metadata && typeof raw.metadata === 'object' ? raw.metadata : undefined,
    timestamp,
  };
}

export function extractReports(raw: unknown): Report[] {
  return extractList<Report>(raw).map(normalizeReport);
}
