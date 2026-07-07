import type { DashboardMetrics } from '@/types';
import { extractObject } from './util';

export function normalizeMetrics(raw: unknown): DashboardMetrics {
  const metrics = extractObject<Record<string, unknown>>(raw);
  return {
    total_transactions: Number(metrics.total_transactions ?? metrics.totalTransactions ?? 0),
    blocked_transactions: Number(metrics.blocked_transactions ?? metrics.blockedTransactions ?? 0),
    review_queue: Number(metrics.review_queue ?? metrics.reviewQueue ?? 0),
    high_risk_count: Number(metrics.high_risk_count ?? metrics.highRiskCount ?? 0),
    cases: Number(metrics.cases ?? metrics.activeCases ?? 0),
    escalations: Number(metrics.escalations ?? metrics.escalations ?? 0),
    p1: Number(metrics.p1 ?? metrics.high_risk_count ?? 0),
    activeCases: Number(metrics.activeCases ?? metrics.cases ?? 0),
    sar: Number(metrics.sar ?? 0),
    mules: Number(metrics.mules ?? 0),
    networkRisk: Number(metrics.networkRisk ?? 0),
  };
}
