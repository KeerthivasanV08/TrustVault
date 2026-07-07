import type { Transaction } from '@/types';
import { store } from '@/store/realtime';

type Handler = (t: Transaction) => void;

export class TransactionStream {
  private es?: EventSource;
  private handlers = new Set<Handler>();
  private url = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000') + '/api/transactions/realtime';
  private reconnectMs = 1000;
  private shouldRun = false;

  onMessage(fn: Handler) { this.handlers.add(fn); return () => this.handlers.delete(fn); }

  start() {
    if (this.shouldRun) return; this.shouldRun = true; this.open();
  }

  stop() { this.shouldRun = false; this.cleanup(); }

  private open() {
    this.cleanup();
    try {
      this.es = new EventSource(this.url);
    } catch (e) {
      this.scheduleReconnect();
      return;
    }
    this.es.onopen = () => { store.setConnectionStatus('connected'); };
    const handlePayload = (ev: MessageEvent) => {
      try { const data = JSON.parse(ev.data); this.handlers.forEach(h => h(data)); } catch (e) { console.error('malformed txn event', e); }
    };
    this.es.onmessage = handlePayload;
    this.es.addEventListener('transaction', handlePayload as EventListener);
    this.es.onerror = () => { store.setConnectionStatus('reconnecting'); this.cleanup(); this.scheduleReconnect(); };
  }

  private scheduleReconnect() {
    if (!this.shouldRun) return;
    setTimeout(() => { this.reconnectMs = Math.min(30_000, Math.floor(this.reconnectMs * 1.5)); this.open(); }, this.reconnectMs);
  }

  private cleanup() { if (this.es) { try { this.es.close(); } catch {} this.es = undefined; } }
}

export default TransactionStream;
