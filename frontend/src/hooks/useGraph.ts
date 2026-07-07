import { useQuery } from '@tanstack/react-query';
import { fetchGraph, fetchGraphNetwork, fetchAccountGraph } from '@/services/api/graph';
import type { GraphData } from '@/types';

export function useGraph() {
  return useQuery<GraphData>({ queryKey: ['graph','network'], queryFn: fetchGraphNetwork, staleTime: 30_000, retry: 2 });
}

export function useGraphSnapshot() {
  return useQuery<GraphData>({ queryKey: ['graph','snapshot'], queryFn: fetchGraph, staleTime: 60_000 });
}

export function useAccountGraph(id?: string) {
  return useQuery({ queryKey: ['graph','account', id], queryFn: () => fetchAccountGraph(id as string), enabled: !!id, staleTime: 30_000 });
}
