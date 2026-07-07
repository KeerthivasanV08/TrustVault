import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Network, ShieldAlert, TriangleAlert } from "lucide-react";

import NetworkGraph from "@/components/NetworkGraph";
import { Panel } from "@/components/aml/Panel";
import { useStore } from "@/store/realtime";
import type { ClusterSummary, GraphData, GraphEdge, GraphNode, Transaction } from "@/types";

export const Route = createFileRoute("/graph")({
  head: () => ({ meta: [{ title: "Graph Explorer — TrustVault" }] }),
  component: GraphPage,
});

const MAX_GRAPH_EDGES = 25;

function GraphPage() {
  const liveTransactions = useStore((state) => state.liveTransactions);
  const connected = useStore((state) => state.connected);

  const investigationGraph = useMemo(
    () => buildInvestigationGraph(liveTransactions),
    [liveTransactions],
  );

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [riskFilter, setRiskFilter] =
    useState<"all" | "high" | "medium" | "low">("all");
  const [showCircularOnly, setShowCircularOnly] = useState(false);
  const [showHighRiskClusters, setShowHighRiskClusters] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  const summary = useMemo(() => {
    const nodes = investigationGraph.nodes ?? [];
    const edges = investigationGraph.edges ?? [];
    const clusterSummaries = investigationGraph.clusterSummaries ?? [];

    const maxClusterRisk = clusterSummaries.length
      ? Math.max(...clusterSummaries.map((cluster) => cluster.avgRisk || 0))
      : 0;

    return {
      nodeCount: nodes.length,
      edgeCount: edges.length,
      clusterCount: clusterSummaries.length,
      circularCount: investigationGraph.circularFlows?.length ?? 0,
      maxClusterRisk,
    };
  }, [investigationGraph]);

  const selected =
    selectedNode ??
    (investigationGraph.selectedAccount
      ? investigationGraph.nodes.find(
          (node) => node.id === investigationGraph.selectedAccount,
        ) ?? null
      : null);

  return (
    <div className="h-full space-y-4 bg-gradient-to-br from-background via-background to-background/90 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            <Network className="h-3.5 w-3.5 text-primary" />
            Neo4j Graph Intelligence
          </div>

          <h1 className="mt-3 text-2xl font-semibold tracking-tight">
            Investigation Graph
          </h1>

          <p className="mt-1 text-sm text-muted-foreground">
            Latest 25 transaction-linked Neo4j nodes for mule-ring, layering,
            shared infrastructure, and fraud proximity investigation.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
          <Stat label="Nodes" value={summary.nodeCount} />
          <Stat label="Edges" value={summary.edgeCount} />
          <Stat label="Clusters" value={summary.clusterCount} />
          <Stat label="Circular" value={summary.circularCount} tone="critical" />
        </div>
      </div>

      <div className="grid min-h-0 gap-4 xl:grid-cols-[260px_minmax(760px,1fr)_320px] 2xl:grid-cols-[280px_minmax(900px,1fr)_360px]">
        <Panel title="Filters" className="min-h-0">
          <div className="space-y-4 text-xs">
            <div>
              <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Risk level
              </div>

              <div className="grid grid-cols-2 gap-2">
                {(["all", "high", "medium", "low"] as const).map((level) => (
                  <button
                    key={level}
                    onClick={() => setRiskFilter(level)}
                    className={`h-8 rounded-md border px-2 text-[10px] uppercase tracking-[0.16em] transition ${
                      riskFilter === level
                        ? "border-primary bg-primary/15 text-primary"
                        : "border-border bg-card/60 text-foreground"
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </div>

            <Toggle
              label="Circular flows only"
              value={showCircularOnly}
              onChange={setShowCircularOnly}
            />

            <Toggle
              label="High-risk clusters only"
              value={showHighRiskClusters}
              onChange={setShowHighRiskClusters}
            />

            <div className="space-y-2 border-t border-border pt-4">
              <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Graph Status
              </div>

              <div className="flex items-center gap-2 rounded-md border border-border bg-card/60 px-3 py-2">
                <ShieldAlert className="h-4 w-4 text-primary" />
                <div>
                  <div className="font-medium">
                    {hydrated ? (connected ? "Connected" : "SSE Waiting") : "SSE Waiting"}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Graph is built from SSE realtime transactions only
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 rounded-md border border-border bg-card/60 px-3 py-2">
                <TriangleAlert className="h-4 w-4 text-warning" />
                <div>
                  <div className="font-medium">
                    Max cluster risk {Math.round(summary.maxClusterRisk)}%
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Derived from latest 25 SSE transaction-linked nodes
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Panel>

        <Panel
          title="Mule Network Graph Explorer"
          subtitle="Interactive transaction network · Click nodes to inspect accounts"
          className="min-h-0"
          dense
        >
          <div className="relative h-[720px] min-h-[720px] w-full overflow-hidden rounded-xl border border-border bg-[#111821] xl:h-[calc(100vh-190px)] xl:min-h-[680px]">
            {investigationGraph.nodes.length ? (
              <NetworkGraph
                nodes={investigationGraph.nodes}
                edges={investigationGraph.edges}
                circularFlows={investigationGraph.circularFlows ?? []}
                clusterSummaries={investigationGraph.clusterSummaries ?? []}
                selectedNodeId={selected?.id}
                onSelectNode={setSelectedNode}
                riskFilter={riskFilter}
                showCircularOnly={showCircularOnly}
                showHighRiskClusters={showHighRiskClusters}
              />
            ) : (
              <div className="flex h-full items-center justify-center px-6 text-center text-sm text-muted-foreground">
                No SSE transaction graph data available. Wait for live transactions or resume the stream.
              </div>
            )}
          </div>
        </Panel>

        <Panel title="Node Detail" className="min-h-0">
          {selected ? (
            <div className="space-y-3 text-xs">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  Selected Node
                </div>
                <div className="mt-1 text-lg font-semibold">
                  {selected.label ?? selected.id}
                </div>
                <div className="text-[11px] text-muted-foreground">
                  {selected.id}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Metric
                  label="Risk"
                  value={Math.round(selected.risk ?? selected.riskScore ?? 0)}
                  tone={
                    (selected.risk ?? selected.riskScore ?? 0) >= 75
                      ? "critical"
                      : "warning"
                  }
                />
                <Metric label="Cluster" value={selected.cluster ?? 0} />
                <Metric label="Volume" value={Math.round(selected.volume ?? 0)} />
                <Metric label="Role" value={selected.role ?? selected.type ?? "unknown"} />
              </div>

              <div className="rounded-md border border-border bg-card/60 p-3">
                <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  Graph Interpretation
                </div>
                <p className="mt-2 text-[12px] leading-5 text-muted-foreground">
                  This node is rendered from live Neo4j account and transfer
                  data. Risk is derived from fraud proximity, layering, shared
                  infrastructure, and community structure.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex h-full min-h-[18rem] items-center justify-center text-sm text-muted-foreground">
              Select a node to inspect its graph signals.
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}

function buildInvestigationGraph(transactions: Transaction[]): GraphData {
  if (!transactions.length) {
    return {
      nodes: [],
      edges: [],
      circularFlows: [],
      clusterSummaries: [],
      metadata: { status: "degraded", source: "sse-realtime" },
    };
  }

  const latestTransactions = [...transactions]
    .sort((left, right) => getTransactionTime(right) - getTransactionTime(left))
    .slice(0, MAX_GRAPH_EDGES);

  const latestEdges = latestTransactions.map((transaction) => ({
    source: transaction.sender,
    target: transaction.receiver,
    amount: transaction.amount,
    weight: transaction.amount,
    suspicious: transaction.decision === "BLOCK" || transaction.riskScore >= 75,
    timestamp: transaction.createdAt ?? transaction.ts,
  }));

  const nodesById = new Map<string, GraphNode>();
  const visibleNodeIds = new Set<string>();
  const visibleNodes: GraphNode[] = [];

  for (const transaction of latestTransactions) {
    const senderNode = buildTransactionNode(transaction, "sender");
    const receiverNode = buildTransactionNode(transaction, "receiver");

    for (const node of [senderNode, receiverNode]) {
      if (!node || visibleNodeIds.has(node.id)) continue;

      nodesById.set(node.id, node);
      visibleNodeIds.add(node.id);
      visibleNodes.push(node);
    }
  }

  for (const edge of latestEdges) {
    for (const nodeId of [edge.source, edge.target]) {
      if (visibleNodeIds.has(nodeId)) continue;

      const fallbackNode = nodesById.get(nodeId);
      if (!fallbackNode) continue;

      visibleNodeIds.add(nodeId);
      visibleNodes.push(fallbackNode);
    }
  }

  const filteredEdges = latestEdges.filter(
    (edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target),
  );

  const clusterSummaries = summarizeClusters(visibleNodes);

  const circularFlows = latestEdges
    .filter((edge) => edge.suspicious)
    .map((edge) => ({ path: [edge.source, edge.target], score: edge.amount }))
    .filter((flow) => flow.path.every((nodeId) => visibleNodeIds.has(nodeId)));

  return {
    nodes: visibleNodes,
    edges: filteredEdges,
    circularFlows,
    clusterSummaries,
    metadata: {
      displayedNodeLimit: visibleNodes.length,
      displayedEdgeLimit: filteredEdges.length,
      displayMode: "latest-25-sse-transactions",
      source: "sse-realtime",
    },
  };
}

function buildTransactionNode(transaction: Transaction, side: "sender" | "receiver"): GraphNode {
  const id = side === "sender" ? transaction.sender : transaction.receiver;
  const label = side === "sender"
    ? transaction.senderName ?? transaction.sender
    : transaction.receiverName ?? transaction.receiver;
  const riskScore = Number(transaction.riskScore ?? 0) || 0;
  const riskLevel = riskScore >= 75 ? "high" : riskScore >= 45 ? "medium" : "low";

  return {
    id,
    label,
    type: side,
    role: side === "sender" ? "SENDER" : "RECEIVER",
    risk: riskScore,
    riskScore,
    riskLevel,
    volume: transaction.amount,
    cluster: riskLevel === "high" ? 1 : riskLevel === "medium" ? 2 : 3,
  };
}

function getTransactionTime(transaction: Transaction): number {
  const candidate = transaction.createdAt ?? transaction.ts;
  const parsed = candidate ? Number(candidate) : NaN;

  return Number.isFinite(parsed) ? parsed : 0;
}

function summarizeClusters(nodes: GraphNode[]): ClusterSummary[] {
  const clusters = new Map<number, GraphNode[]>();

  for (const node of nodes) {
    const clusterId = Number.isFinite(Number(node.cluster))
      ? Number(node.cluster)
      : 0;

    const clusterNodes = clusters.get(clusterId) ?? [];
    clusterNodes.push(node);
    clusters.set(clusterId, clusterNodes);
  }

  return [...clusters.entries()]
    .map(([id, items]) => {
      const totalRiskScore = items.reduce(
        (sum, item) => sum + (Number(item.risk ?? item.riskScore ?? 0) || 0),
        0,
      );

      const avgRisk = items.length ? totalRiskScore / items.length : 0;

      return {
        id,
        name: `Cluster ${id}`,
        accounts: items.length,
        totalRiskScore: Number(totalRiskScore.toFixed(2)),
        avgRisk: Number(avgRisk.toFixed(2)),
        hasCircularFlow: avgRisk >= 70,
        color: avgRisk >= 70 ? "#ef4444" : avgRisk >= 45 ? "#f59e0b" : "#22c55e",
      };
    })
    .sort((left, right) => left.id - right.id);
}

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number;
  tone?: "default" | "critical";
}) {
  return (
    <div className="rounded-md border border-border bg-card/60 px-3 py-2 text-right">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </div>
      <div
        className={`mt-1 text-lg font-semibold ${
          tone === "critical" ? "text-critical" : "text-foreground"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

function Toggle({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-left transition ${
        value ? "border-primary bg-primary/15" : "border-border bg-card/60"
      }`}
    >
      <span>{label}</span>
      <span
        className={`h-4 w-8 rounded-full border transition ${
          value ? "border-primary bg-primary/60" : "border-border bg-muted"
        }`}
      >
        <span
          className={`block h-3 w-3 translate-y-0.5 rounded-full bg-background transition ${
            value ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </span>
    </button>
  );
}

function Metric({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string | number;
  tone?: "default" | "critical" | "warning";
}) {
  return (
    <div className="rounded-md border border-border bg-card/60 px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </div>
      <div
        className={`mt-1 text-sm font-medium ${
          tone === "critical"
            ? "text-critical"
            : tone === "warning"
              ? "text-warning"
              : "text-foreground"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
