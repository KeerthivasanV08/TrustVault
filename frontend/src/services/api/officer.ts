import client from './client';

export async function review(payload: any) {
  return client.request({ method: 'POST', path: '/api/officer/review', body: payload });
}

export async function freeze(payload: any) {
  return client.request({ method: 'POST', path: '/api/officer/freeze', body: payload });
}

export async function escalate(payload: any) {
  return client.request({ method: 'POST', path: '/api/officer/escalate', body: payload });
}

export async function sar(payload: any, timeoutMs: number = 60000) {
  const caseId = payload?.case_id;
  if (caseId) {
    return client.request({
      method: 'POST',
      path: `/api/officer/reports/generate-sar/case/${encodeURIComponent(String(caseId))}`,
      body: payload,
      timeoutMs,
    });
  }

  const alertId = payload?.alert_id ?? payload?.alertId ?? payload?.source_alert ?? payload?.sourceAlert;
  if (alertId) {
    return client.request({
      method: 'POST',
      path: `/api/officer/reports/generate-sar/alert/${encodeURIComponent(String(alertId))}`,
      body: payload,
      timeoutMs,
    });
  }

  return client.request({ method: 'POST', path: '/api/officer/sar', body: payload, timeoutMs });
}

export async function createOfficerCase(payload: any) {
  return client.request({ method: 'POST', path: '/api/officer/case/create', body: payload });
}

export async function fetchOfficerCases() {
  return client.request({ path: '/api/officer/case/all' });
}

export async function resolveOfficerCase(payload: any) {
  return client.request({ method: 'POST', path: '/api/officer/case/resolve', body: payload });
}

export async function whitelistOfficer(payload: any) {
  return client.request({ method: 'POST', path: '/api/officer/whitelist', body: payload });
}
