import client from './client';
import type { Transaction } from '@/types';
import { extractTransactions, normalizeTransaction } from '@/lib/normalizers/transactionNormalizer';

export async function fetchRecentTransactions(): Promise<Transaction[]> {
  const raw = await client.request<unknown>({ path: '/api/transactions/recent' });
  return extractTransactions(raw);
}

export async function analyzeTransaction(body: Partial<Transaction>): Promise<Transaction> {
  const raw = await client.request<unknown>({ method: 'POST', path: '/api/transactions', body });
  return normalizeTransaction(raw);
}

export { normalizeTransaction };
