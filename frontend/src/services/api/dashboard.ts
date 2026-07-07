import client from './client';
import type { DashboardMetrics } from '@/types';
import { normalizeMetrics } from '@/lib/normalizers/metricsNormalizer';

export async function fetchDashboardMetrics(): Promise<DashboardMetrics> {
  const raw = await client.request<unknown>({ path: '/api/dashboard/metrics' });
  return normalizeMetrics(raw);
}
