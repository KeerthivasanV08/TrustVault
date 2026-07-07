import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { ArrowRightLeft, AlertTriangle, ShieldCheck, Waves } from 'lucide-react';
import { fetchTransactions } from '@/services/api';
import { useAmlSocket } from '@/hooks/useAmlSocket';
import { useAmlStore } from '@/app/store/amlStore';
import type { AmlRealtimeTransaction } from '@/types/aml';

function normalizeDisplayRisk(transaction: AmlRealtimeTransaction) {
  return transaction.riskScore;
}

function riskClass(score: number) {
  if (score >= 90) return 'border-risk-high/40 bg-risk-high/10 text-risk-high shadow-[0_0_28px_rgba(239,68,68,0.18)]';
  if (score >= 75) return 'border-risk-high/25 bg-risk-high/5 text-risk-high';
  if (score >= 50) return 'border-risk-medium/25 bg-risk-medium/5 text-risk-medium';
  return 'border-risk-low/25 bg-risk-low/5 text-risk-low';
}

export function TransactionIntelFeed() {
  const connectionState = useAmlSocket(true);
  const realtimeTransactions = useAmlStore((state) => state.realtimeTransactions);
  const { data: historicalTransactions = [], isLoading, error } = useQuery({
    queryKey: ['aml', 'transaction-feed'],
    queryFn: fetchTransactions,
    refetchInterval: 3000,
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  const combinedFeed = useMemo(() => {
    const mappedHistorical = historicalTransactions.map((transaction: any): AmlRealtimeTransaction => ({
      id: String(transaction.trans_id ?? transaction.id),
      senderId: String(transaction.sender_id ?? transaction.from ?? 'UNKNOWN'),
      receiverId: String(transaction.receiver_id ?? transaction.to ?? 'UNKNOWN'),
      amount: Number(transaction.amount ?? 0),
      timestamp: String(transaction.timestamp ?? new Date().toISOString()),
      decision: String(transaction.decision ?? transaction.status ?? 'ALLOW').toUpperCase() as AmlRealtimeTransaction['decision'],
      riskScore: Number(transaction.risk_score ?? transaction.risk ?? 0),
      behaviorScore: Number(transaction.behavior_score ?? 0),
      sequenceScore: Number(transaction.sequence_score ?? 0),
      graphScore: Number(transaction.graph_score ?? 0),
      confidence: Number(transaction.confidence ?? 0),
      ruleTriggers: Array.isArray(transaction.reasons) ? transaction.reasons : [],
      graphProximity: String(transaction.graph_proximity ?? transaction.cluster_risk ?? 'UNKNOWN'),
      forwardingDelayMins: Number(transaction.forwarding_delay_mins ?? 0),
      txnVelocity1h: Number(transaction.txn_velocity_1h ?? 0),
      drainRatio: Number(transaction.drain_ratio ?? 0),
      deviceIntelligence: String(transaction.device_intelligence ?? 'NORMAL'),
      geoRisk: Number(transaction.geo_risk ?? 0),
      timestampDriftMins: Number(transaction.timestamp_drift ?? 0),
      officerEscalationStatus: String(transaction.officer_recommendation ?? 'NONE'),
      reportTypes: Array.isArray(transaction.report_types) ? transaction.report_types : [],
      priority: Number(transaction.risk_score ?? transaction.risk ?? 0) >= 75 ? 'P1' : Number(transaction.risk_score ?? transaction.risk ?? 0) >= 50 ? 'P2' : 'P3',
      isMuleCluster: Boolean(transaction.cluster_risk === 'HIGH' || transaction.is_mule_cluster),
      raw: transaction,
    }));

    return [...realtimeTransactions, ...mappedHistorical]
      .sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime())
      .slice(0, 25);
  }, [historicalTransactions, realtimeTransactions]);

  return (
    <div className="glass-panel overflow-hidden">
      <div className="border-b border-border/60 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Transaction Intelligence Feed</h2>
            <p className="text-xs text-muted-foreground">Bloomberg-style AML stream with realtime risk enrichment.</p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Waves className="h-3.5 w-3.5 text-primary animate-pulse" /> {connectionState.toUpperCase()}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-background/80 backdrop-blur">
            <tr className="border-b border-border/60 text-left text-xs uppercase tracking-[0.16em] text-muted-foreground">
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Sender</th>
              <th className="px-4 py-3">Receiver</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Decision</th>
              <th className="px-4 py-3">Risk</th>
              <th className="px-4 py-3">Scores</th>
              <th className="px-4 py-3">Signals</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {isLoading && Array.from({ length: 8 }).map((_, index) => (
              <tr key={index}>
                <td colSpan={8} className="px-4 py-4">
                  <div className="h-5 animate-pulse rounded-full bg-muted/70" />
                </td>
              </tr>
            ))}

            {!isLoading && error && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-sm text-risk-high">Unable to load transaction feed.</td>
              </tr>
            )}

            {!isLoading && !error && combinedFeed.map((transaction, index) => {
              const riskScore = normalizeDisplayRisk(transaction);
              return (
                <motion.tr
                  key={`${transaction.id}-${index}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2 }}
                  className={`transition-colors hover:bg-card/60 ${riskClass(riskScore)} ${riskScore >= 90 ? 'animate-pulse' : ''}`}
                >
                  <td className="px-4 py-4 text-xs text-muted-foreground">{new Date(transaction.timestamp).toLocaleTimeString()}</td>
                  <td className="px-4 py-4 font-medium text-foreground">{transaction.senderId}</td>
                  <td className="px-4 py-4 font-medium text-foreground">{transaction.receiverId}</td>
                  <td className="px-4 py-4 font-semibold text-foreground">₹{transaction.amount.toLocaleString()}</td>
                  <td className="px-4 py-4">
                    <span className="rounded-full border border-border/60 bg-card/60 px-2 py-1 text-xs font-semibold">{transaction.decision}</span>
                  </td>
                  <td className="px-4 py-4 font-semibold">{riskScore}%</td>
                  <td className="px-4 py-4 text-xs text-muted-foreground">
                    B {transaction.behaviorScore}% • S {transaction.sequenceScore}% • G {transaction.graphScore}%
                    <div className="mt-1">Conf {transaction.confidence}% • Drift {transaction.timestampDriftMins}m</div>
                  </td>
                  <td className="px-4 py-4 text-xs text-muted-foreground">
                    <div className="flex flex-wrap gap-1">
                      {transaction.ruleTriggers.slice(0, 2).map((trigger) => (
                        <span key={trigger} className="rounded-full border border-border/60 bg-card/60 px-2 py-1">{trigger}</span>
                      ))}
                      {transaction.isMuleCluster && (
                        <span className="rounded-full border border-risk-high/30 bg-risk-high/10 px-2 py-1 text-risk-high">Mule Cluster</span>
                      )}
                    </div>
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="border-t border-border/60 p-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-3.5 w-3.5 text-risk-low" />
          Live feed updates arrive via SSE and are cached in Zustand for graph, alerts, investigation, and case workflows.
        </div>
      </div>
    </div>
  );
}
