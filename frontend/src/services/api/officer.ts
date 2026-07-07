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

export async function sar(payload: any) {
  return client.request({ method: 'POST', path: '/api/officer/sar', body: payload });
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
