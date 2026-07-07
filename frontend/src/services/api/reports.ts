import client from './client';
import type { Report } from '@/types';
import { extractReports } from '@/lib/normalizers/reportNormalizer';

export async function fetchReports(): Promise<Report[]> {
  const raw = await client.request<unknown>({ path: '/api/reports' });
  return extractReports(raw);
}

export async function fetchSarReports(): Promise<Report[]> {
  const raw = await client.request<unknown>({ path: '/api/reports/sar' });
  return extractReports(raw);
}

export async function fetchStrReports(): Promise<Report[]> {
  const raw = await client.request<unknown>({ path: '/api/reports/str' });
  return extractReports(raw);
}

export async function fetchHighRiskReports(): Promise<Report[]> {
  const raw = await client.request<unknown>({ path: '/api/reports/high-risk' });
  return extractReports(raw);
}

export async function fetchManualReviewReports(): Promise<Report[]> {
  const raw = await client.request<unknown>({ path: '/api/reports/manual-review' });
  return extractReports(raw);
}

export async function exportReport(format: 'json'|'csv'|'pdf') {
  return client.request({ path: `/api/reports/export?format=${format}` });
}
