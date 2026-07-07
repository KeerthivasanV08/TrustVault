import { useQuery } from '@tanstack/react-query';
import { fetchAccounts, fetchAccountById, type AccountListResponse } from '@/services/api/accounts';
import type { Account } from '@/types';

export function useAccounts() {
  return useQuery<Account[]>({ queryKey: ['accounts','list'], queryFn: () => fetchAccounts().then((payload) => payload.results), staleTime: 60_000, retry: 2 });
}

export function useAccountList(params: { limit?: number; search?: string; risk?: string; offset?: number } = {}) {
  return useQuery<AccountListResponse>({ queryKey: ['accounts', 'list', params], queryFn: () => fetchAccounts(params), staleTime: 60_000, retry: 2 });
}

export function useAccount(id?: string) {
  return useQuery<Account | undefined>({ queryKey: ['accounts', id], queryFn: () => fetchAccountById(id as string), enabled: !!id, staleTime: 60_000 });
}
