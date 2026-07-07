import type {
  Account,
  Alert,
  GraphData,
  ReportsData,
  Transaction,
} from '@/types/api';
import type { AmlCase } from '@/types/aml';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

const API_ENDPOINTS = {
  transactions: '/api/transactions/recent',
  transactionRealtime: '/api/transactions/realtime',
  transactionAnalyze: '/api/transactions/analyze',
  accounts: '/api/accounts',
  alerts: '/api/alerts',
  graph: '/api/graph/network',
  onboardingEvaluate: '/api/onboarding/evaluate',
  onboardingExplain: '/api/onboarding/explain',
  officerReview: '/api/officer/review',
  officerFreeze: '/api/officer/freeze',
  officerSar: '/api/officer/sar',
  reports: '/api/reports',
  reportsExport: '/api/reports/export',
} as const;

function toArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${path}`);
  }

  return (await response.json()) as T;
}

async function requestText(path: string, init: RequestInit = {}): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: 'text/plain, application/json',
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${path}`);
  }

  return response.text();
}

export async function fetchTransactions(): Promise<Transaction[]> {
  const payload = await requestJson<Transaction[] | { items?: Transaction[] }>(API_ENDPOINTS.transactions);
  return Array.isArray(payload) ? payload : toArray<Transaction>(payload.items);
}

export async function fetchRealtimeTransactions(): Promise<Transaction[]> {
  const payload = await requestJson<Transaction[] | { items?: Transaction[] }>(API_ENDPOINTS.transactionRealtime);
  return Array.isArray(payload) ? payload : toArray<Transaction>(payload.items);
}

export async function fetchAccounts(): Promise<Account[]> {
  const payload = await requestJson<Account[] | { items?: Account[] }>(API_ENDPOINTS.accounts);
  return Array.isArray(payload) ? payload : toArray<Account>(payload.items);
}

export async function fetchAlerts(): Promise<Alert[]> {
  const payload = await requestJson<Alert[] | { items?: Alert[] }>(API_ENDPOINTS.alerts);
  return Array.isArray(payload) ? payload : toArray<Alert>(payload.items);
}

export async function fetchGraphData(): Promise<GraphData> {
  const payload = await requestJson<Partial<GraphData>>(API_ENDPOINTS.graph);
  return {
    nodes: toArray(payload.nodes),
    edges: toArray(payload.edges),
    circularFlows: toArray(payload.circularFlows),
    clusterSummaries: toArray(payload.clusterSummaries),
  };
}

export async function fetchSystemHealth(): Promise<{
  readiness: { status: string; runtime_mode?: string; ml_engine?: string; graph_engine?: string; control_engine?: string };
  modelHealth: { behavioral_model: string; sequence_model: string; graph_engine: string; runtime_mode: string };
}> {
  const [readiness, modelHealth] = await Promise.all([
    requestJson<{ status: string; runtime_mode?: string; ml_engine?: string; graph_engine?: string; control_engine?: string }>('/api/ready'),
    requestJson<{ behavioral_model: string; sequence_model: string; graph_engine: string; runtime_mode: string }>('/api/system/model-health'),
  ]);

  return { readiness, modelHealth };
}

export async function fetchAccountGraph(accountId: string): Promise<GraphData> {
  const payload = await requestJson<Partial<GraphData>>(`/api/graph/account/${encodeURIComponent(accountId)}`);
  return {
    nodes: toArray(payload.nodes),
    edges: toArray(payload.edges),
    circularFlows: toArray(payload.circularFlows),
    clusterSummaries: toArray(payload.clusterSummaries),
  };
}

export async function evaluateOnboarding(payload: unknown): Promise<unknown> {
  return requestJson(API_ENDPOINTS.onboardingEvaluate, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function explainOnboarding(userId: string): Promise<unknown> {
  return requestJson(`${API_ENDPOINTS.onboardingExplain}/${encodeURIComponent(userId)}`);
}

export async function analyzeTransaction(payload: unknown): Promise<unknown> {
  return requestJson(API_ENDPOINTS.transactionAnalyze, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchOfficerCases(): Promise<AmlCase[]> {
  const payload = await requestJson<AmlCase[] | { items?: AmlCase[] }>('/api/officer/case/all');
  return Array.isArray(payload) ? payload : toArray<AmlCase>(payload.items);
}

export async function fetchOfficerReviewQueue(): Promise<AmlCase[]> {
  return fetchOfficerCases();
}

export async function submitOfficerFreeze(payload: unknown): Promise<unknown> {
  return requestJson(API_ENDPOINTS.officerFreeze, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function submitOfficerSar(payload: unknown): Promise<unknown> {
  return requestJson(API_ENDPOINTS.officerSar, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchReports(): Promise<ReportsData> {
  const payload = await requestJson<Partial<ReportsData>>(API_ENDPOINTS.reports);
  return {
    officers: toArray<string>(payload.officers),
    auditTrail: toArray(payload.auditTrail),
  };
}

export async function exportReports(format: 'json' | 'csv' | 'pdf' = 'json'): Promise<string> {
  return requestText(`${API_ENDPOINTS.reportsExport}?format=${encodeURIComponent(format)}`);
}
