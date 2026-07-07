import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { CircularFlow, ClusterSummary, GraphEdge, GraphNode } from "@/types";
import { ANIMATION_TIMING, HIGH_RISK_CLUSTER_THRESHOLD } from "@/lib/constants";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  circularFlows: CircularFlow[];
  clusterSummaries: ClusterSummary[];
  onSelectNode?: (node: GraphNode) => void;
  selectedNodeId?: string | null;
  riskFilter?: string;
  showCircularOnly?: boolean;
  showHighRiskClusters?: boolean;
}

type RiskLevel = "high" | "medium" | "low";

function toFiniteNumber(value: unknown, fallback = 0): number {
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function getRiskScore(node: GraphNode): number {
  return toFiniteNumber(node.risk ?? node.riskScore ?? 0, 0);
}

function getRiskLevel(node: GraphNode): RiskLevel {
  const explicit = typeof node.riskLevel === "string" ? node.riskLevel.toLowerCase() : "";
  if (explicit === "high" || explicit === "medium" || explicit === "low") {
    return explicit;
  }

  const score = getRiskScore(node);
  if (score >= 75) return "high";
  if (score >= 45) return "medium";
  return "low";
}

function getNodeRadius(riskLevel: RiskLevel): number {
  if (riskLevel === "high") return 28;
  if (riskLevel === "medium") return 18;
  return 15;
}

function getNodeFill(riskLevel: RiskLevel): string {
  if (riskLevel === "high") return "#ef4444";
  if (riskLevel === "medium") return "#f59e0b";
  return "#22c55e";
}

function getNodeGlow(riskLevel: RiskLevel): string {
  if (riskLevel === "high") return "drop-shadow(0 0 12px rgba(239,68,68,0.75))";
  if (riskLevel === "medium") return "drop-shadow(0 0 10px rgba(245,158,11,0.45))";
  return "drop-shadow(0 0 8px rgba(34,197,94,0.35))";
}

function normalizeCluster(summary: ClusterSummary): ClusterSummary {
  return {
    ...summary,
    id: toFiniteNumber(summary.id, 0),
    accounts: toFiniteNumber(summary.accounts, 0),
    totalRiskScore: toFiniteNumber(summary.totalRiskScore, 0),
    avgRisk: toFiniteNumber(summary.avgRisk, 0),
  };
}

function layoutNodes(nodes: GraphNode[], width: number, height: number): GraphNode[] {
  if (!nodes.length) {
    return [];
  }

  const safeWidth = Math.max(width, 1);
  const safeHeight = Math.max(height, 1);
  const withCoords = nodes.filter((node) => Number.isFinite(node.x) && Number.isFinite(node.y));

  if (withCoords.length > 0) {
    const xs = withCoords.map((node) => toFiniteNumber(node.x, 0));
    const ys = withCoords.map((node) => toFiniteNumber(node.y, 0));
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const spanX = Math.max(maxX - minX, 1);
    const spanY = Math.max(maxY - minY, 1);
    const padding = Math.max(96, Math.min(safeWidth, safeHeight) * 0.12);
    const scale = Math.min((safeWidth - padding * 2) / spanX, (safeHeight - padding * 2) / spanY);
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    return nodes.map((node, index) => {
      if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) {
        return placeFallbackNode(node, index, nodes.length, safeWidth, safeHeight);
      }

      const riskLevel = getRiskLevel(node);
      let x = (toFiniteNumber(node.x, 0) - centerX) * scale + safeWidth / 2;
      let y = (toFiniteNumber(node.y, 0) - centerY) * scale + safeHeight / 2;
      const offsetX = x - safeWidth / 2;
      const offsetY = y - safeHeight / 2;
      const distance = Math.hypot(offsetX, offsetY) || 1;
      const pull = riskLevel === "high" ? -0.12 : riskLevel === "medium" ? -0.05 : 0.04;
      const nudge = Math.min(safeWidth, safeHeight) * 0.08 * pull;
      x += (offsetX / distance) * nudge;
      y += (offsetY / distance) * nudge;

      return {
        ...node,
        x: clamp(x, 56, safeWidth - 56),
        y: clamp(y, 56, safeHeight - 56),
      };
    });
  }

  return nodes
    .slice()
    .sort((left, right) => getRiskScore(right) - getRiskScore(left))
    .map((node, index, ordered) => placeFallbackNode(node, index, ordered.length, safeWidth, safeHeight));
}

function placeFallbackNode(node: GraphNode, index: number, total: number, width: number, height: number): GraphNode {
  const centerX = width / 2;
  const centerY = height / 2;
  const baseRadius = Math.min(width, height) * 0.46;
  const riskLevel = getRiskLevel(node);
  const radiusMultiplier = riskLevel === "high" ? 0.42 : riskLevel === "medium" ? 0.68 : 0.92;
  const radius = baseRadius * radiusMultiplier;
  const angle = (Math.PI * 2 * index) / Math.max(total, 1) - Math.PI / 2;

  return {
    ...node,
    x: clamp(centerX + Math.cos(angle) * radius, 56, width - 56),
    y: clamp(centerY + Math.sin(angle) * radius, 56, height - 56),
  };
}

function buildAdjacency(edges: GraphEdge[]): Map<string, Set<string>> {
  const adjacency = new Map<string, Set<string>>();

  for (const edge of edges) {
    const sourceNeighbors = adjacency.get(edge.source) ?? new Set<string>();
    sourceNeighbors.add(edge.target);
    adjacency.set(edge.source, sourceNeighbors);

    const targetNeighbors = adjacency.get(edge.target) ?? new Set<string>();
    targetNeighbors.add(edge.source);
    adjacency.set(edge.target, targetNeighbors);
  }

  return adjacency;
}

function buildCircularEdgeKeys(circularFlows: CircularFlow[]): Set<string> {
  const keys = new Set<string>();

  for (const flow of circularFlows) {
    for (let index = 0; index < flow.path.length - 1; index += 1) {
      keys.add(`${flow.path[index]}->${flow.path[index + 1]}`);
    }
  }

  return keys;
}

function useViewportSize<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [size, setSize] = useState({ width: 1200, height: 680 });

  useEffect(() => {
    const element = ref.current;
    if (!element) {
      return;
    }

    const updateSize = () => {
      const rect = element.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        setSize({ width: Math.round(rect.width), height: Math.round(rect.height) });
      }
    };

    updateSize();

    const observer = new ResizeObserver(() => updateSize());
    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  return { ref, size };
}

export default function NetworkGraph({
  nodes,
  edges,
  circularFlows,
  clusterSummaries,
  onSelectNode,
  selectedNodeId,
  riskFilter,
  showCircularOnly,
  showHighRiskClusters,
}: Props) {
  const { ref, size } = useViewportSize<HTMLDivElement>();
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [localSelectedNodeId, setLocalSelectedNodeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (selectedNodeId) {
      setLocalSelectedNodeId(selectedNodeId);
    }
  }, [selectedNodeId]);

  const normalizedClusters = useMemo(() => clusterSummaries.map(normalizeCluster), [clusterSummaries]);
  const laidOutNodes = useMemo(() => {
    return layoutNodes(
      nodes.map((node) => ({
        ...node,
        volume: toFiniteNumber(node.volume, 0),
        cluster: toFiniteNumber(node.cluster, 0),
      })),
      size.width,
      size.height,
    ).map((node) => ({
      ...node,
      riskLevel: getRiskLevel(node),
    }));
  }, [nodes, size.width, size.height]);

  const circularNodeIds = useMemo(() => new Set(circularFlows.flatMap((flow) => flow.path)), [circularFlows]);
  const circularEdgeKeys = useMemo(() => buildCircularEdgeKeys(circularFlows), [circularFlows]);

  const visibleNodes = useMemo(() => {
    let nextNodes = riskFilter && riskFilter !== "all"
      ? laidOutNodes.filter((node) => node.riskLevel === riskFilter)
      : [...laidOutNodes];

    if (showHighRiskClusters) {
      const highRiskClusterIds = new Set(
        normalizedClusters
          .filter((summary) => summary.avgRisk >= HIGH_RISK_CLUSTER_THRESHOLD)
          .map((summary) => summary.id),
      );
      nextNodes = nextNodes.filter((node) => highRiskClusterIds.has(toFiniteNumber(node.cluster, 0)));
    }

    if (showCircularOnly) {
      nextNodes = nextNodes.filter((node) => circularNodeIds.has(node.id));
    }

    return nextNodes;
  }, [laidOutNodes, riskFilter, showHighRiskClusters, showCircularOnly, circularNodeIds, normalizedClusters]);

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((node) => node.id)), [visibleNodes]);
  const visibleEdges = useMemo(() => {
    return edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target));
  }, [edges, visibleNodeIds]);

  const adjacency = useMemo(() => buildAdjacency(visibleEdges), [visibleEdges]);
  const focusNodeId = hoveredNodeId ?? localSelectedNodeId ?? selectedNodeId ?? null;

  const activeNode = useMemo(() => {
    if (!focusNodeId) {
      return null;
    }
    return visibleNodes.find((node) => node.id === focusNodeId) ?? null;
  }, [focusNodeId, visibleNodes]);

  const relatedNodeIds = useMemo(() => {
    if (!activeNode) {
      return null;
    }

    const related = new Set<string>([activeNode.id]);
    for (const neighbor of adjacency.get(activeNode.id) ?? []) {
      related.add(neighbor);
    }
    return related;
  }, [activeNode, adjacency]);

  const selectedNode = activeNode ?? null;

  const tooltipNode = hoveredNodeId ? visibleNodes.find((node) => node.id === hoveredNodeId) ?? null : null;
  const tooltipPosition = tooltipNode
    ? {
        left: clamp((toFiniteNumber(tooltipNode.x, 0) * zoom) + pan.x + 18, 16, Math.max(16, size.width - 220)),
        top: clamp((toFiniteNumber(tooltipNode.y, 0) * zoom) + pan.y - 74, 16, Math.max(16, size.height - 120)),
      }
    : null;

  const handleNodeClick = useCallback((node: GraphNode) => {
    setLocalSelectedNodeId(node.id);
    onSelectNode?.(node);
  }, [onSelectNode]);

  const handleMouseDown = (event: React.MouseEvent) => {
    const target = event.target as HTMLElement;
    if (target === event.currentTarget || target.tagName === "svg") {
      setDragging(true);
      setDragStart({ x: event.clientX - pan.x, y: event.clientY - pan.y });
    }
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    if (dragging) {
      setPan({ x: event.clientX - dragStart.x, y: event.clientY - dragStart.y });
    }
  };

  const handleMouseUp = () => setDragging(false);

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const activeConnectedNodeIds = useMemo(() => {
    if (!selectedNode) {
      return null;
    }

    const ids = new Set<string>([selectedNode.id]);
    for (const neighbor of adjacency.get(selectedNode.id) ?? []) {
      ids.add(neighbor);
    }
    return ids;
  }, [selectedNode, adjacency]);

  if (nodes.length === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
        No graph data available yet
      </div>
    );
  }

  return (
    <div ref={ref} className="relative h-full w-full overflow-hidden bg-[#111821]">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage: [
            "radial-gradient(circle at center, rgba(59,130,246,0.10), transparent 34%)",
            "linear-gradient(180deg, rgba(15,23,42,0.96), rgba(2,6,23,0.99))",
            "linear-gradient(rgba(148,163,184,0.05) 1px, transparent 1px)",
            "linear-gradient(90deg, rgba(148,163,184,0.05) 1px, transparent 1px)",
          ].join(", "),
          backgroundSize: "100% 100%, 100% 100%, 64px 64px, 64px 64px",
          backgroundPosition: "center",
        }}
      />

      <div className="absolute right-3 top-3 z-20 flex flex-col gap-2">
        <button
          type="button"
          onClick={() => setZoom((next) => Math.min(ANIMATION_TIMING.ZOOM_MAX, next + 0.12))}
          className="flex h-9 w-9 items-center justify-center rounded-md border border-white/10 bg-slate-950/75 text-lg font-semibold text-slate-100 shadow-lg backdrop-blur-sm transition hover:border-slate-400/50 hover:bg-slate-900"
          aria-label="Zoom in"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => setZoom((next) => Math.max(ANIMATION_TIMING.ZOOM_MIN, next - 0.12))}
          className="flex h-9 w-9 items-center justify-center rounded-md border border-white/10 bg-slate-950/75 text-lg font-semibold text-slate-100 shadow-lg backdrop-blur-sm transition hover:border-slate-400/50 hover:bg-slate-900"
          aria-label="Zoom out"
        >
          -
        </button>
        <button
          type="button"
          onClick={resetView}
          className="flex h-9 w-9 items-center justify-center rounded-md border border-white/10 bg-slate-950/75 text-xs font-semibold uppercase tracking-[0.18em] text-slate-100 shadow-lg backdrop-blur-sm transition hover:border-slate-400/50 hover:bg-slate-900"
          aria-label="Reset zoom"
        >
          R
        </button>
      </div>

      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${size.width} ${size.height}`}
        preserveAspectRatio="xMidYMid meet"
        className="absolute inset-0 h-full w-full cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <defs>
          <pattern id="graph-grid" width="64" height="64" patternUnits="userSpaceOnUse">
            <path d="M 64 0 L 0 0 0 64" fill="none" stroke="rgba(148,163,184,0.10)" strokeWidth="1" />
          </pattern>
          <radialGradient id="graph-halo" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(59,130,246,0.16)" />
            <stop offset="70%" stopColor="rgba(59,130,246,0.06)" />
            <stop offset="100%" stopColor="rgba(59,130,246,0)" />
          </radialGradient>
          <linearGradient id="edge-muted" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgba(51,65,85,0.22)" />
            <stop offset="100%" stopColor="rgba(71,85,105,0.55)" />
          </linearGradient>
        </defs>

        <rect x={0} y={0} width={size.width} height={size.height} fill="#111821" />
        <rect x={0} y={0} width={size.width} height={size.height} fill="url(#graph-grid)" opacity={0.45} />
        <ellipse cx={size.width / 2} cy={size.height / 2} rx={Math.min(size.width, size.height) * 0.42} ry={Math.min(size.width, size.height) * 0.34} fill="url(#graph-halo)" opacity={0.9} />

        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {normalizedClusters.map((cluster) => {
            const clusterNodes = visibleNodes.filter((node) => toFiniteNumber(node.cluster, 0) === cluster.id);
            if (clusterNodes.length < 2) {
              return null;
            }

            const centerX = clusterNodes.reduce((sum, node) => sum + toFiniteNumber(node.x, 0), 0) / clusterNodes.length;
            const centerY = clusterNodes.reduce((sum, node) => sum + toFiniteNumber(node.y, 0), 0) / clusterNodes.length;
            const distances = clusterNodes.map((node) => Math.hypot(toFiniteNumber(node.x, 0) - centerX, toFiniteNumber(node.y, 0) - centerY));
            const spread = (distances.length ? Math.max(...distances) : 0) + 64;

            return (
              <ellipse
                key={cluster.id}
                cx={centerX}
                cy={centerY}
                rx={spread * 1.16}
                ry={spread * 0.86}
                fill={cluster.color ?? "rgba(148,163,184,0.12)"}
                fillOpacity={0.04}
                stroke={cluster.color ?? "rgba(148,163,184,0.22)"}
                strokeOpacity={0.20}
                strokeWidth={1.4}
                strokeDasharray="6 4"
              />
            );
          })}

          {visibleEdges.map((edge, index) => {
            const source = visibleNodes.find((node) => node.id === edge.source);
            const target = visibleNodes.find((node) => node.id === edge.target);
            if (!source || !target) {
              return null;
            }

            const isSuspicious = edge.suspicious || circularEdgeKeys.has(`${edge.source}->${edge.target}`);
            const isFocused = !selectedNode || edge.source === selectedNode.id || edge.target === selectedNode.id || (activeConnectedNodeIds?.has(edge.source) && activeConnectedNodeIds?.has(edge.target));
            const stroke = isSuspicious ? "#ef4444" : "url(#edge-muted)";
            const strokeWidth = isSuspicious ? 2.5 : 1.4;
            const strokeOpacity = selectedNode ? (isFocused ? (isSuspicious ? 0.95 : 0.78) : 0.14) : (isSuspicious ? 0.9 : 0.45);

            return (
              <line
                key={`${edge.source}-${edge.target}-${index}`}
                x1={toFiniteNumber(source.x, 0)}
                y1={toFiniteNumber(source.y, 0)}
                x2={toFiniteNumber(target.x, 0)}
                y2={toFiniteNumber(target.y, 0)}
                stroke={stroke}
                strokeWidth={strokeWidth}
                strokeOpacity={strokeOpacity}
                strokeDasharray={isSuspicious ? "6 5" : undefined}
                strokeLinecap="round"
              />
            );
          })}

          {visibleNodes.map((node) => {
            const riskLevel = getRiskLevel(node);
            const radius = getNodeRadius(riskLevel);
            const isHovered = hoveredNodeId === node.id;
            const isSelected = selectedNode?.id === node.id;
            const isConnected = !selectedNode || selectedNode.id === node.id || activeConnectedNodeIds?.has(node.id);
            const connectedCount = adjacency.get(node.id)?.size ?? 0;
            const opacity = selectedNode ? (isConnected ? 1 : 0.25) : (hoveredNodeId && !isHovered ? 0.78 : 1);

            return (
              <g key={node.id} transform={`translate(${toFiniteNumber(node.x, 0)}, ${toFiniteNumber(node.y, 0)})`} opacity={opacity}>
                <circle
                  r={radius + (isHovered || isSelected ? 9 : 6)}
                  fill="none"
                  stroke={riskLevel === "high" ? "rgba(239,68,68,0.34)" : riskLevel === "medium" ? "rgba(245,158,11,0.26)" : "rgba(34,197,94,0.22)"}
                  strokeWidth={2}
                />
                <circle
                  r={radius + (riskLevel === "high" ? 16 : 12)}
                  fill={riskLevel === "high" ? "rgba(239,68,68,0.12)" : riskLevel === "medium" ? "rgba(245,158,11,0.10)" : "rgba(34,197,94,0.08)"}
                />
                <circle
                  r={radius}
                  fill={getNodeFill(riskLevel)}
                  stroke={isSelected ? "#f8fafc" : riskLevel === "high" ? "rgba(255,255,255,0.22)" : "rgba(255,255,255,0.12)"}
                  strokeWidth={isSelected ? 3 : 1.4}
                  style={{ filter: getNodeGlow(riskLevel) }}
                  className="cursor-pointer transition-transform duration-150"
                  transform={isHovered ? "scale(1.08)" : isSelected ? "scale(1.05)" : "scale(1)"}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                  onClick={() => handleNodeClick(node)}
                />
                {riskLevel === "high" && (
                  <circle
                    r={radius + 11}
                    fill="none"
                    stroke="rgba(239,68,68,0.95)"
                    strokeWidth={1.5}
                    strokeDasharray="4 3"
                    opacity={0.72}
                  />
                )}

                <text
                  x={0}
                  y={radius + 18}
                  textAnchor="middle"
                  fill="#cbd5e1"
                  stroke="#020617"
                  strokeWidth={3}
                  paintOrder="stroke fill"
                  fontSize={11}
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace"
                  fontWeight={600}
                  opacity={selectedNode && !isConnected ? 0.45 : 1}
                >
                  {node.label ?? node.id}
                </text>

                {isHovered && (
                  <text
                    x={0}
                    y={-radius - 16}
                    textAnchor="middle"
                    fill="#dbeafe"
                    stroke="#020617"
                    strokeWidth={3}
                    paintOrder="stroke fill"
                    fontSize={10}
                    fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace"
                  >
                    {connectedCount} connections
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {tooltipNode && tooltipPosition && (
        <div
          className="pointer-events-none absolute z-20 w-[220px] rounded-lg border border-white/10 bg-slate-950/92 p-3 text-[11px] text-slate-100 shadow-2xl backdrop-blur-md"
          style={{ left: tooltipPosition.left, top: tooltipPosition.top }}
        >
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Node inspection</div>
          <div className="mt-1 font-semibold text-slate-50">{tooltipNode.label ?? tooltipNode.id}</div>
          <div className="mt-0.5 font-mono text-[10px] text-slate-400">{tooltipNode.id}</div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] text-slate-300">
            <span>Risk: {getRiskLevel(tooltipNode).toUpperCase()}</span>
            <span>Score: {Math.round(getRiskScore(tooltipNode))}</span>
            <span>Role: {tooltipNode.role ?? tooltipNode.type ?? "unknown"}</span>
            <span>Connected: {adjacency.get(tooltipNode.id)?.size ?? 0}</span>
          </div>
        </div>
      )}

      <div className="pointer-events-none absolute bottom-3 left-3 z-20 flex flex-wrap gap-2 rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-[11px] text-slate-200 shadow-xl backdrop-blur-md">
        <LegendSwatch label="High" color="#ef4444" />
        <LegendSwatch label="Medium" color="#f59e0b" />
        <LegendSwatch label="Low" color="#22c55e" />
        <span className="flex items-center gap-2 text-slate-300">
          <span className="h-0.5 w-5 rounded-full bg-[#ef4444]" style={{ boxShadow: "0 0 10px rgba(239,68,68,0.6)" }} />
          Suspicious
        </span>
      </div>
    </div>
  );
}

function LegendSwatch({ label, color }: { label: string; color: string }) {
  return (
    <span className="flex items-center gap-2 text-slate-300">
      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color, boxShadow: `0 0 10px ${color}66` }} />
      {label}
    </span>
  );
}
