const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://127.0.0.1:8000";

export type RequestOptions = {
  method?: string;
  path: string;
  body?: any;
  signal?: AbortSignal;
  timeoutMs?: number;
  headers?: Record<string,string>;
};

class APIError extends Error {
  public status?: number;
  public data?: any;
  constructor(message: string, status?: number, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export async function request<T>({ method = 'GET', path, body, signal, timeoutMs = 15000, headers }: RequestOptions): Promise<T> {
  const url = API_BASE.replace(/\/$/, '') + path;
  const controller = new AbortController();
  const mergedSignal = controller.signal;
  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  const opts: RequestInit = { method, headers: { 'content-type': 'application/json', ...(headers || {}) }, credentials: 'omit', signal: mergedSignal };
  if (body != null) opts.body = JSON.stringify(body);

  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.debug('[API] request', { method, url, body, timeoutMs });
  }

  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const r = await fetch(url, opts);
    if (!r.ok) {
      let data: any = null;
      try { data = await r.json(); } catch (e) { data = await r.text().catch(()=>null); }
      throw new APIError(r.statusText || 'API Error', r.status, data);
    }
    const text = await r.text();
    if (!text) return null as unknown as T;
    try {
      const parsed = JSON.parse(text) as T;
      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.debug('[API] response', { path, status: r.status, data: parsed });
      }
      return parsed;
    } catch {
      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.debug('[API] response text', { path, status: r.status, text });
      }
      return text as unknown as T;
    }
  } catch (err: any) {
    if (controller.signal.aborted) throw new APIError('Request timed out');
    if (err?.name === 'AbortError') throw new APIError('Request aborted');
    if (err?.message === 'Failed to fetch' || String(err?.message || '').includes('fetch')) throw new APIError('Backend unavailable');
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export default { request, API_BASE, APIError };
