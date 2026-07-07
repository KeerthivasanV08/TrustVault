import type { GraphData, GraphNode, GraphEdge } from '@/types';
import { extractGraphPayload } from './util';

function safeNumber(value: unknown, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function assignCoordinates(nodes: GraphNode[]): GraphNode[] {
  const count = nodes.length;
  if (!count) return nodes;
  const centerX = 500;
  const centerY = 300;
  const radius = 200;
  return nodes.map((node, index) => {
    if (typeof node.x === 'number' && typeof node.y === 'number') return node;
    const angle = (index / count) * Math.PI * 2;
    return {
      ...node,
      x: typeof node.x === 'number' ? node.x : Math.round(centerX + radius * Math.cos(angle)),
      y: typeof node.y === 'number' ? node.y : Math.round(centerY + radius * Math.sin(angle)),
    };
  });
}

export function normalizeGraph(raw: unknown): GraphData {
  const payload = extractGraphPayload(raw);
  const nodes = payload.nodes.map((node: any) => ({
    id: String(node?.id ?? node?.node_id ?? node?.entity_id ?? node?.label ?? ''),
    label: node?.label ?? node?.name ?? String(node?.id ?? node?.node_id ?? node?.entity_id ?? ''),
    type: node?.type ?? node?.node_type ?? node?.entity_type,
    role: node?.role ?? node?.network_role ?? node?.category,
    risk: safeNumber(node?.risk ?? node?.risk_level ?? node?.riskScore ?? node?.score ?? 0),
    riskScore: safeNumber(node?.riskScore ?? node?.risk ?? node?.risk_level ?? node?.score ?? 0),
    riskLevel: node?.riskLevel ?? node?.risk_level,
    x: node?.x != null ? safeNumber(node.x) : undefined,
    y: node?.y != null ? safeNumber(node.y) : undefined,
    volume: node?.volume != null ? safeNumber(node.volume) : undefined,
    cluster: node?.cluster != null ? safeNumber(node.cluster) : undefined,
  }));

  const positioned = assignCoordinates(nodes);

  const edges = payload.edges.map((edge: any) => ({
    source: String(edge?.source ?? edge?.from ?? edge?.source_id ?? edge?.from_id ?? ''),
    target: String(edge?.target ?? edge?.to ?? edge?.target_id ?? edge?.to_id ?? ''),
    weight: edge?.weight != null ? safeNumber(edge.weight) : undefined,
    amount: edge?.amount != null ? safeNumber(edge.amount) : undefined,
    suspicious: Boolean(edge?.suspicious ?? false),
  })).filter((edge) => edge.source && edge.target);

  const circularFlows = Array.isArray(payload.circularFlows)
    ? payload.circularFlows.map((flow: any) => ({
        path: Array.isArray(flow?.path) ? flow.path.map((item: any) => String(item)) : [],
        score: flow?.score != null ? safeNumber(flow.score) : undefined,
        label: flow?.label ? String(flow.label) : undefined,
      })).filter((flow: any) => flow.path.length > 0)
    : [];

  const clusterSummaries = Array.isArray(payload.clusterSummaries)
    ? payload.clusterSummaries.map((summary: any) => ({
        id: safeNumber(summary?.id, 0),
        name: summary?.name ? String(summary.name) : `Cluster ${safeNumber(summary?.id, 0)}`,
        accounts: safeNumber(summary?.accounts, 0),
        totalRiskScore: safeNumber(summary?.totalRiskScore, 0),
        avgRisk: safeNumber(summary?.avgRisk, 0),
        hasCircularFlow: Boolean(summary?.hasCircularFlow ?? false),
        color: summary?.color ? String(summary.color) : undefined,
      }))
    : [];

  return {
    nodes: positioned,
    edges,
    circularFlows,
    clusterSummaries,
    selectedAccount: typeof payload.selectedAccount === 'string' ? payload.selectedAccount : undefined,
    updatedAt: typeof payload.updatedAt === 'string' ? payload.updatedAt : undefined,
    metadata: payload.metadata && typeof payload.metadata === 'object' ? (payload.metadata as Record<string, unknown>) : undefined,
  };
}
