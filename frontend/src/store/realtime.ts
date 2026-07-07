// Lightweight realtime store (no external deps) — SSE-driven
import { useEffect, useState } from 'react';
import type { Transaction, Alert, DashboardMetrics, QueueSnapshot } from '@/types';

interface State {
  connected: boolean;
  connectionStatus: 'connected' | 'disconnected' | 'reconnecting';
  paused: boolean;
  transactions: Transaction[];
  liveTransactions: Transaction[];
  alerts: Alert[];
  liveAlerts: Alert[];
  liveCases: unknown[];
  liveGraphEvents: unknown[];
  selectedAlert: Alert | null;
  selectedCase: unknown | null;
  dashboardMetrics: DashboardMetrics | null;
  queueState: QueueSnapshot | null;
  slaState: Record<string, unknown>;
  ticker: { ts: number; level: string; text: string }[];
  metrics: Record<string, number>;
}

let state: State = {
  connected: false,
  connectionStatus: 'disconnected',
  paused: false,
  transactions: [],
  liveTransactions: [],
  alerts: [],
  liveAlerts: [],
  liveCases: [],
  liveGraphEvents: [],
  selectedAlert: null,
  selectedCase: null,
  dashboardMetrics: null,
  queueState: null,
  slaState: {},
  ticker: [],
  metrics: {},
};

const listeners = new Set<() => void>();
const notify = () => listeners.forEach((l) => l());

export const store = {
  get: () => state,
  set: (next: Partial<State>) => { state = { ...state, ...next }; notify(); },
  subscribe: (fn: () => void) => { listeners.add(fn); return () => listeners.delete(fn); },
  togglePause: () => store.set({ paused: !state.paused }),
  pauseLiveView: () => store.set({ paused: true }),
  resumeLiveView: () => store.set({ paused: false }),
  setConnected: (c: boolean) => store.set({ connected: c, connectionStatus: c ? 'connected' : 'disconnected' }),
  setConnectionStatus: (connectionStatus: State['connectionStatus']) => store.set({ connectionStatus, connected: connectionStatus === 'connected' }),
  pushTransaction: (t: Transaction) => {
    store.addTransactionFromSSE(t);
    const amount = Number(t.amount) || 0;
    const formattedAmount = new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amount);
    store.addTickerLine({
      ts: Date.now(),
      level: t.riskScore >= 80 ? 'critical' : 'warning',
      text: `Txn ${t.id.slice(0, 8)} · ${t.sender.slice(-6)} → ${t.receiver.slice(-6)} · ${formattedAmount} · risk ${Math.round(t.riskScore)}%`,
    });
  },
  pushAlert: (a: Alert) => {
    store.addAlertFromSSE(a);
    store.addTickerLine({
      ts: Date.now(),
      level: a.priority === 'P1' ? 'critical' : a.priority === 'P2' ? 'warning' : 'success',
      text: `${a.priority} · ${a.type} · ${a.summary ?? 'Alert triggered'} · risk ${Math.round(a.riskScore)}%`,
    });
  },
  setTicker: (lines: { ts: number; level: string; text: string }[]) => {
    state = { ...state, ticker: lines.slice(0, 200) };
    notify();
  },
  addTickerLine: (line: { ts: number; level: string; text: string }) => {
    state = { ...state, ticker: [line, ...state.ticker].slice(0, 200) };
    notify();
  },
  updateMetrics: (m: Record<string, number>) => { state = { ...state, metrics: { ...state.metrics, ...m } }; notify(); },
  updateDashboardMetrics: (m: DashboardMetrics) => {
    state = {
      ...state,
      dashboardMetrics: m,
      metrics: {
        ...state.metrics,
        totalTxn: m.total_transactions,
        blocked: m.blocked_transactions,
        reviewQueue: m.review_queue,
        p1: m.high_risk_count,
        activeCases: m.cases,
        networkRisk: m.escalations,
      },
    };
    notify();
  },
  updateQueueFromAPI: (queueState: QueueSnapshot) => { state = { ...state, queueState }; notify(); },
  addTransactionFromSSE: (t: Transaction) => {
    state = {
      ...state,
      transactions: [t, ...state.transactions.filter((x) => x.id !== t.id)].slice(0, 500),
      liveTransactions: [t, ...state.liveTransactions.filter((x) => x.id !== t.id)].slice(0, 500),
    };
    notify();
  },
  addAlertFromSSE: (a: Alert) => {
    state = {
      ...state,
      alerts: [a, ...state.alerts.filter((x) => x.id !== a.id)].slice(0, 500),
      liveAlerts: [a, ...state.liveAlerts.filter((x) => x.id !== a.id)].slice(0, 500),
    };
    notify();
  },
  setSelectedAlert: (selectedAlert: Alert | null) => store.set({ selectedAlert }),
  setSelectedCase: (selectedCase: unknown | null) => store.set({ selectedCase }),
  clear: () => { state = { connected: false, connectionStatus: 'disconnected', paused: false, transactions: [], liveTransactions: [], alerts: [], liveAlerts: [], liveCases: [], liveGraphEvents: [], selectedAlert: null, selectedCase: null, dashboardMetrics: null, queueState: null, slaState: {}, ticker: [], metrics: {} }; notify(); },
};

export function useStore<T>(selector: (s: State) => T): T {
  const [val, setVal] = useState(() => selector(state));
  useEffect(() => {
    const unsub = store.subscribe(() => setVal(selector(state)));
    return () => { unsub(); };
  }, []);
  return val;
}

// Utility to merge historical results (e.g., from TanStack Query) into the realtime list
export function mergeHistoricalTransactions(hist: Transaction[]) {
  const map = new Map<string, Transaction>();
  hist.forEach(t => map.set(t.id, t));
  state.transactions.forEach(t => map.set(t.id, t));
  state.liveTransactions.forEach(t => map.set(t.id, t));
  const merged = Array.from(map.values()).sort((a,b) => b.ts - a.ts).slice(0,500);
  store.set({ transactions: merged, liveTransactions: merged });
}

// Merge historical alerts into realtime alerts list
export function mergeHistoricalAlerts(hist: Alert[]) {
  const map = new Map<string, Alert>();
  hist.forEach(a => map.set(a.id, a));
  state.alerts.forEach(a => map.set(a.id, a));
  state.liveAlerts.forEach(a => map.set(a.id, a));
  const merged = Array.from(map.values()).sort((a,b) => (b.createdAt || 0) - (a.createdAt || 0)).slice(0,500);
  store.set({ alerts: merged, liveAlerts: merged });
}

