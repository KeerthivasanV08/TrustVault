import { useQuery, useMutation } from '@tanstack/react-query';
import { fetchCases, fetchCase, createCase, assignCase, freezeCase, sarCase } from '@/services/api/cases';
import type { Case } from '@/types';

export function useCases() {
  return useQuery<Case[]>({ queryKey: ['cases','list'], queryFn: fetchCases, staleTime: 30_000, retry: 2 });
}

export function useCase(id?: string) {
  return useQuery({ queryKey: ['cases', id], queryFn: () => fetchCase(id as string), enabled: !!id });
}

export function useCreateCase() { return useMutation({ mutationFn: (p: Partial<Case>) => createCase(p) }); }
export function useAssignCase() { return useMutation({ mutationFn: ({ id, officerId }: { id: string; officerId: string }) => assignCase(id, officerId) }); }
export function useFreezeCase() { return useMutation({ mutationFn: (id: string) => freezeCase(id) }); }
export function useSarCase() { return useMutation({ mutationFn: (id: string) => sarCase(id) }); }
