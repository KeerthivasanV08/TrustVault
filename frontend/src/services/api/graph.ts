import client from './client';
import type { GraphData } from '@/types';
import { normalizeGraph } from '@/lib/normalizers/graphNormalizer';

export async function fetchGraph(): Promise<GraphData> {
  return fetchGraphNetwork();
}

export async function fetchGraphNetwork(): Promise<GraphData> {
  const raw = await client.request<unknown>({ path: '/api/graph/network' });
  return normalizeGraph(raw);
}

export async function fetchAccountGraph(id: string) {
  try {
    const raw = await client.request<unknown>({ path: `/api/graph/account/${encodeURIComponent(id)}` });
    return normalizeGraph(raw);
  } catch {
    return fetchGraphNetwork();
  }
}

export async function fetchGraphRisk(accountId: string): Promise<unknown> {
  return client.request({ path: `/api/graph/risk/${encodeURIComponent(accountId)}` });
}

export async function fetchGraphLayering(accountId: string): Promise<unknown> {
  return client.request({ path: `/api/graph/layering/${encodeURIComponent(accountId)}` });
}

export async function fetchGraphCommunity(accountId: string): Promise<unknown> {
  return client.request({ path: `/api/graph/community/${encodeURIComponent(accountId)}` });
}
