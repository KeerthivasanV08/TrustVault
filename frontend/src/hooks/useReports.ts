import { useQuery, useMutation } from '@tanstack/react-query';
import { fetchReports, exportReport, fetchSarReports, fetchStrReports, fetchHighRiskReports, fetchManualReviewReports } from '@/services/api/reports';
import type { Report } from '@/types';

export function useReports() {
  return useQuery<Report[]>({ queryKey: ['reports','list'], queryFn: fetchReports, staleTime: 60_000 });
}

export function useSarReports() { return useQuery<Report[]>({ queryKey: ['reports','sar'], queryFn: fetchSarReports, staleTime: 60_000 }); }
export function useStrReports() { return useQuery<Report[]>({ queryKey: ['reports','str'], queryFn: fetchStrReports, staleTime: 60_000 }); }
export function useHighRiskReports() { return useQuery<Report[]>({ queryKey: ['reports','high-risk'], queryFn: fetchHighRiskReports, staleTime: 60_000 }); }
export function useManualReviewReports() { return useQuery<Report[]>({ queryKey: ['reports','manual-review'], queryFn: fetchManualReviewReports, staleTime: 60_000 }); }

export function useExportReport() { return useMutation({ mutationFn: (fmt: 'json'|'csv'|'pdf') => exportReport(fmt) }); }
