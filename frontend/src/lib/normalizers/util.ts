export function extractList<T>(raw: unknown): T[] {
  if (Array.isArray(raw)) return raw as T[];
  if (!raw || typeof raw !== 'object') return [];
  const candidate = raw as Record<string, unknown>;
  for (const key of ['items', 'data', 'results', 'payload']) {
    const value = candidate[key];
    if (Array.isArray(value)) return value as T[];
  }
  return [];
}

export function extractObject<T extends object>(raw: unknown): T {
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) return raw as T;
  return {} as T;
}

export function extractGraphPayload(raw: unknown): { nodes: any[]; edges: any[] } {
  if (!raw || typeof raw !== 'object') return { nodes: [], edges: [] };
  const payload = raw as Record<string, unknown>;
  const nodes = Array.isArray(payload.nodes)
    ? payload.nodes
    : Array.isArray(payload.data?.nodes)
      ? payload.data?.nodes as any[]
      : Array.isArray(payload.items?.nodes)
        ? payload.items?.nodes as any[]
        : [];
  const edges = Array.isArray(payload.edges)
    ? payload.edges
    : Array.isArray(payload.data?.edges)
      ? payload.data?.edges as any[]
      : Array.isArray(payload.items?.edges)
        ? payload.items?.edges as any[]
        : [];
  return { nodes, edges };
}
