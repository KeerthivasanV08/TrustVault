import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Toaster } from "sonner";

import appCss from "../styles.css?url";
import { Sidebar } from "@/components/aml/Sidebar";
import { Header } from "@/components/aml/Header";
import { RealtimeThreatFeed } from "@/components/aml/RealtimeThreatFeed";
import { store } from "@/store/realtime";
import TransactionStream from '@/services/sse/transactionStream';
import AlertStream from '@/services/sse/alertStream';
import { fetchAlertEscalations, normalizeAlert } from '@/services/api/alerts';
import { normalizeTransaction } from '@/services/api/transactions';
function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold mono text-primary">404</h1>
        <h2 className="mt-4 text-xl font-semibold">Route not found in console</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The operational surface you requested does not exist.
        </p>
        <Link to="/" className="mt-6 inline-flex h-9 px-4 items-center justify-center rounded-md bg-primary text-primary-foreground text-sm">
          Return to Command Center
        </Link>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  const router = useRouter();
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold">Console error</h1>
        <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
        <button onClick={() => { router.invalidate(); reset(); }} className="mt-4 h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm">
          Retry
        </button>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "TrustVault — AML Operations Console" },
      { name: "description", content: "Real-time AML intelligence platform for fraud analysts, investigators and compliance officers." },
      { name: "theme-color", content: "#0a1019" },
    ],
    links: [{ rel: "stylesheet", href: appCss }],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head><HeadContent /></head>
      <body className="dark">
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const router = useRouter();
  const pathname = router.state.location.pathname;
  const showLiveThreatFeed = pathname === "/";
  useEffect(() => {
    // Start SSE streams and wire into realtime store + merge into query cache
    const txs = new TransactionStream();
    const als = new AlertStream();
    const unsubTx = txs.onMessage((tRaw) => {
      try {
        const t = normalizeTransaction(tRaw);
        store.pushTransaction(t);
        store.setConnected(true);
        store.addTickerLine({
          ts: Date.now(),
          level: t.riskScore >= 80 ? 'critical' : 'warning',
          text: `Txn ${t.id.slice(0, 8)} ${t.sender.slice(-6)}→${t.receiver.slice(-6)} · ${t.currency} ${t.amount.toLocaleString()} · risk ${Math.round(t.riskScore)}%`,
        });
        // merge into transactions.recent cache
        queryClient.setQueryData(['transactions','recent'], (old: any) => {
          const arr = (old || []) as any[];
          return [t, ...arr.filter((x) => x.id !== t.id)].slice(0, 500);
        });
        // optimistic merge into dashboard metrics
        queryClient.setQueryData(['dashboard','metrics'], (old: any) => {
          if (!old) return old;
          try {
            const copy = { ...old };
            copy.total_transactions = (copy.total_transactions || 0) + 1;
            if (t.decision && t.decision.toString().toUpperCase().includes('BLOCK')) {
              copy.blocked_transactions = (copy.blocked_transactions || 0) + 1;
            }
            if (typeof t.riskScore === 'number' && t.riskScore >= 80) {
              copy.high_risk_count = (copy.high_risk_count || 0) + 1;
            }
            return copy;
          } catch (e) { return old; }
        });
        // merge into graph snapshot: add nodes/edge
        queryClient.setQueryData(['graph','snapshot'], (old: any) => {
          if (!old) return old;
          try {
            const nodes: any[] = Array.isArray(old.nodes) ? [...old.nodes] : [];
            const edges: any[] = Array.isArray(old.edges) ? [...old.edges] : [];
            const ensureNode = (id: string) => {
              if (!nodes.find(n => n.id === id)) nodes.push({ id, label: id.slice(-8) });
            };
            ensureNode(t.sender);
            ensureNode(t.receiver);
            const existing = edges.find(e => e.source === t.sender && e.target === t.receiver);
            if (existing) {
              existing.weight = (existing.weight || 0) + 1;
            } else {
              edges.push({ source: t.sender, target: t.receiver, weight: 1 });
            }
            return { ...old, nodes, edges };
          } catch (e) { return old; }
        });
      } catch (e) { console.error('txn sse merge err', e); }
    });
    const unsubAl = als.onMessage((aRaw) => {
      try {
        const a = normalizeAlert(aRaw);
        store.pushAlert(a);
        store.setConnected(true);
        store.addTickerLine({
          ts: Date.now(),
          level: a.priority === 'P1' ? 'critical' : a.priority === 'P2' ? 'warning' : 'success',
          text: `${a.priority} · ${a.type} · ${a.summary ?? 'Alert triggered'} · risk ${Math.round(a.riskScore)}%`,
        });
        // merge into alerts.list
        queryClient.setQueryData(['alerts','list'], (old: any) => {
          const arr = (old || []) as any[];
          return [a, ...arr.filter((x) => x.id !== a.id)].slice(0, 500);
        });
        // if P1, also merge into P1 cache
        if (a.priority === 'P1') {
          queryClient.setQueryData(['alerts','p1'], (old: any) => {
            const arr = (old || []) as any[];
            return [a, ...arr.filter((x) => x.id !== a.id)].slice(0, 500);
          });
        }
        // optimistic dashboard updates for alerts
        queryClient.setQueryData(['dashboard','metrics'], (old: any) => {
          if (!old) return old;
          try {
            const copy = { ...old };
            copy.review_queue = (copy.review_queue || 0) + 1;
            if (a.priority === 'P1') copy.high_risk_count = (copy.high_risk_count || 0) + 1;
            return copy;
          } catch (e) { return old; }
        });
        // merge into officer queue cache (used by officer widgets)
        queryClient.setQueryData(['officer','queues'], (old: any) => {
          try {
            const arr = Array.isArray(old) ? [...old] : [];
            const item = { id: a.id, alertId: a.id, assignedTo: a.assignedOfficer ?? null, priority: a.priority };
            return [item, ...arr.filter((x: any) => x.id !== a.id)].slice(0, 500);
          } catch (e) { return old; }
        });
        // merge into reports cache if present (best-effort)
        queryClient.setQueryData(['reports','list'], (old: any) => {
          if (!old) return old;
          try { return old; } catch (e) { return old; }
        });
      } catch (e) { console.error('alert sse merge err', e); }
    });
    txs.start(); als.start();
    return () => { unsubTx(); unsubAl(); txs.stop(); als.stop(); };
  }, [queryClient]);
  return (
    <QueryClientProvider client={queryClient}>
      <div className="h-screen flex bg-background text-foreground overflow-hidden">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Header />
          <div className="flex-1 flex min-h-0">
            <main className="flex-1 overflow-y-auto scrollbar-thin min-w-0">
              <Outlet />
            </main>
            {showLiveThreatFeed && (
              <aside className="w-72 shrink-0 border-l border-border hidden xl:flex flex-col p-3 gap-3">
                <RealtimeThreatFeed compact />
                <EscalationsPanel />
              </aside>
            )}
          </div>
        </div>
        <Toaster theme="dark" position="bottom-right" toastOptions={{ style: { background: "var(--color-card)", border: "1px solid var(--color-border)", color: "var(--color-foreground)" } }} />
      </div>
    </QueryClientProvider>
  );
}

function EscalationsPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["alerts", "escalations"],
    queryFn: fetchAlertEscalations,
    staleTime: 10_000,
    retry: 1,
    refetchInterval: 30_000,
  });

  const breaches = Array.isArray(data)
    ? data
        .map((item: any) => {
          const alertId = String(item?.alert_id ?? item?.alertId ?? item?.id ?? "");
          const summary = String(item?.summary ?? item?.reason ?? item?.description ?? item?.txt ?? "SLA breach");
          const time = String(item?.t ?? item?.time ?? item?.delta ?? "");
          return { alertId, summary, time };
        })
        .filter((item) => item.alertId)
    : [];

  return (
    <div className="glass-panel rounded-lg p-3 text-xs min-h-0 flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] uppercase tracking-[0.18em] font-medium">SLA Breaches</span>
        <span className="text-[10px] mono text-critical">{isLoading ? "..." : `${breaches.length} ACTIVE`}</span>
      </div>
      {isError ? (
        <div className="text-[11px] text-muted-foreground">Realtime SLA data unavailable.</div>
      ) : breaches.length ? (
        <ul className="space-y-1.5 overflow-y-auto min-h-0 scrollbar-thin pr-1">
          {breaches.slice(0, 5).map((b) => (
            <li key={b.alertId} className="flex items-center justify-between gap-3 p-2 rounded border border-critical/30 bg-critical/5">
              <div className="min-w-0">
                <div className="mono text-[11px] whitespace-normal break-words">{b.alertId}</div>
                <div className="text-[10px] text-muted-foreground whitespace-normal break-words leading-relaxed">{b.summary}</div>
              </div>
              <span className="mono text-[11px] text-critical shrink-0">{b.time || "breached"}</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="text-[11px] text-muted-foreground">No active SLA breaches</div>
      )}
    </div>
  );
}
