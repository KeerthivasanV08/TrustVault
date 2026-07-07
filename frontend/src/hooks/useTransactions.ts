import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchRecentTransactions, analyzeTransaction, normalizeTransaction } from '@/services/api/transactions';
import type { Transaction } from '@/types';

export function useRecentTransactions() {
  const qc = useQueryClient();
  const q = useQuery<Transaction[]>({
    queryKey: ['transactions','recent'],
    queryFn: async () => {
      const data = await fetchRecentTransactions();
      return (data || []).map(normalizeTransaction);
    },
    staleTime: 10_000,
    retry: 2,
    refetchInterval: 30_000,
  });

  // Mutation to analyze/send a transaction
  const mutation = useMutation({
    mutationFn: (tx: Partial<Transaction>) => analyzeTransaction(tx),
    onSuccess: (res) => {
      // prepend to cache
      qc.setQueryData(['transactions','recent'], (old: any) => {
        const arr = (old || []) as Transaction[];
        return [res, ...arr.filter((t) => t.id !== res.id)].slice(0,500);
      });
    }
  });

  return { ...q, analyze: mutation.mutateAsync };
}
