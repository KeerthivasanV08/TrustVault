import type { Transaction } from '@/types';
import { extractList } from './util';

import type { Transaction } from '@/types';
import { extractList } from './util';

export function normalizeTransaction(raw: any): Transaction {
  const id = String(raw?.id ?? raw?.trans_id ?? raw?.transaction_id ?? raw?.txn_id ?? '');
  
  // Handle timestamp: prefer ISO string, fallback to number
  let ts: number | undefined;
  let timestamp: string | number | undefined;
  
  if (raw?.timestamp) {
    if (typeof raw.timestamp === 'string') {
      timestamp = raw.timestamp;
      const parsed = new Date(raw.timestamp).getTime();
      if (!Number.isNaN(parsed)) ts = parsed;
    } else {
      ts = Number(raw.timestamp);
    }
  } else if (raw?.ts || raw?.created_at || raw?.createdAt) {
    ts = Number(raw?.ts ?? raw?.created_at ?? raw?.createdAt ?? Date.now());
  }
  
  if (!ts && !Number.isNaN(new Date(timestamp).getTime())) {
    ts = new Date(String(timestamp)).getTime();
  }
  ts = ts || Date.now();
  
  const riskScore = Number(raw?.riskScore ?? raw?.final_score ?? raw?.finalScore ?? 0);
  const behavioralScore = Number(raw?.behavioral_score ?? raw?.behaviorScore ?? raw?.behavioralScore ?? 0);
  return {
    id,
    transactionId: raw?.transaction_id ?? raw?.trans_id ?? id,
    ts,
    timestamp,
    createdAt: ts,
    sender: String(raw?.sender ?? raw?.sender_id ?? raw?.from ?? ''),
    senderName: raw?.senderName ?? raw?.sender_name ?? raw?.fromName ?? '',
    receiver: String(raw?.receiver ?? raw?.receiver_id ?? raw?.to ?? ''),
    receiverName: raw?.receiverName ?? raw?.receiver_name ?? raw?.toName ?? '',
    amount: Number(raw?.amount ?? 0),
    currency: String(raw?.currency ?? raw?.ccy ?? 'INR'),
    channel: raw?.channel ? String(raw.channel) : undefined,
    countryFrom: raw?.countryFrom ?? raw?.country_from,
    countryTo: raw?.countryTo ?? raw?.country_to,
    decision: String(raw?.decision ?? 'ALLOW').toUpperCase() as Transaction['decision'],
    riskScore,
    finalScore: Number(raw?.final_score ?? raw?.finalScore ?? riskScore),
    behaviorScore: behavioralScore,
    behavioralScore,
    sequenceScore: Number(raw?.sequence_score ?? raw?.sequenceScore ?? 0),
    graphScore: Number(raw?.graph_score ?? raw?.graphScore ?? 0),
    ruleScore: Number(raw?.rule_score ?? raw?.ruleScore ?? 0),
    signals: extractList<string>(raw?.signals ?? raw?.signal_list ?? raw?.signal ?? []),
    status: String(raw?.status ?? raw?.state ?? 'PENDING'),
  };
}

export function extractTransactions(raw: unknown): Transaction[] {
  return extractList<Transaction>(raw).map(normalizeTransaction);
}
