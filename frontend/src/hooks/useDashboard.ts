import { useQuery } from '@tanstack/react-query';
import { fetchDashboardMetrics } from '@/services/api/dashboard';
import type { DashboardMetrics } from '@/types';

export function useDashboardMetrics() {
  const opts = {
    queryKey: ['dashboard','metrics'] as const,
    queryFn: fetchDashboardMetrics,
    staleTime: 10_000,
    retry: 2,
    refetchInterval: 30_000,
  } as const;
  try {
    return useQuery<DashboardMetrics>(opts as any);
  } catch (e) {
    // Log the options shape if react-query throws to aid debugging
    // eslint-disable-next-line no-console
    console.error('useDashboardMetrics - useQuery called with invalid args', { opts, err: e });
    throw e;
  }
}
