import client from './client';
import type { Alert, QueueSnapshot } from '@/types';
import { extractAlerts } from '@/lib/normalizers/alertNormalizer';

export async function fetchAlerts(): Promise<Alert[]> {
  const raw = await client.request<unknown>({ path: '/api/alerts' });
  return extractAlerts(raw);
}

export async function fetchP1Alerts(): Promise<Alert[]> {
  const raw = await client.request<unknown>({ path: '/api/alerts/p1' });
  return extractAlerts(raw);
}

export async function fetchP2Alerts(): Promise<Alert[]> {
  const raw = await client.request<unknown>({ path: '/api/alerts/p2' });
  return extractAlerts(raw);
}

export async function fetchOfficerAlerts(officerId: string): Promise<Alert[]> {
  const raw = await client.request<unknown>({ path: `/api/alerts/officer/${encodeURIComponent(officerId)}` });
  return extractAlerts(raw);
}

export async function fetchAlertsQueue(): Promise<QueueSnapshot> {
  return client.request<QueueSnapshot>({ path: '/api/alerts/queue' });
}

export async function fetchAlertEscalations(): Promise<unknown[]> {
  const raw = await client.request<unknown>({ path: '/api/alerts/escalations' });
  return Array.isArray(raw) ? raw : [];
}

export { normalizeAlert } from '@/lib/normalizers/alertNormalizer';

export async function acknowledgeAlert(id: string): Promise<void> {
  await client.request<void>({ method: 'POST', path: `/api/alerts/${id}/acknowledge` });
}

export async function escalateAlert(id: string): Promise<void> {
  await client.request<void>({ method: 'POST', path: `/api/alerts/${id}/escalate` });
}

export async function closeAlert(id: string): Promise<void> {
  await client.request<void>({ method: 'POST', path: `/api/alerts/${id}/close` });
}
