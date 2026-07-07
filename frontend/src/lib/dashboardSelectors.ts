import type { Transaction, Alert } from '@/types';

function formatWindow(ts: number): string {
  const d = new Date(ts);
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

export function buildRiskTrend(transactions: Transaction[], alerts: Alert[]) {
  const now = Date.now();
  const windowMs = 60 * 60 * 1000;
  const buckets: Record<number, { totalRisk: number; count: number; alerts: number }> = {};

  const transactionBuckets = transactions.slice().sort((a, b) => a.ts - b.ts).map((txn) => {
    const bucket = Math.floor(txn.ts / windowMs) * windowMs;
    const entry = buckets[bucket] ?? { totalRisk: 0, count: 0, alerts: 0 };
    entry.totalRisk += txn.finalScore ?? txn.riskScore ?? 0;
    entry.count += 1;
    buckets[bucket] = entry;
    return txn;
  });

  alerts.forEach((alert) => {
    const bucket = Math.floor(alert.createdAt / windowMs) * windowMs;
    const entry = buckets[bucket] ?? { totalRisk: 0, count: 0, alerts: 0 };
    entry.alerts += 1;
    buckets[bucket] = entry;
  });

  const bucketKeys = Array.from(new Set(Object.keys(buckets).map(Number))).sort((a, b) => a - b);
  const latest = bucketKeys.length ? bucketKeys[bucketKeys.length - 1] : Math.floor(now / windowMs) * windowMs;
  const series: { window: string; risk: number; alerts: number }[] = [];
  for (let i = 29; i >= 0; i -= 1) {
    const ts = latest - i * windowMs;
    const bucket = buckets[ts];
    series.push({
      window: formatWindow(ts),
      risk: bucket && bucket.count ? +(bucket.totalRisk / bucket.count).toFixed(2) : 0,
      alerts: bucket?.alerts ?? 0,
    });
  }
  return series;
}

export function buildRiskDistribution(transactions: Transaction[], alerts: Alert[]) {
  const values = transactions.map((txn) => txn.finalScore ?? txn.riskScore ?? 0);
  const buckets = {
    LOW: 0,
    MEDIUM: 0,
    HIGH: 0,
    CRITICAL: 0,
  } as Record<string, number>;

  values.forEach((score) => {
    if (score > 0.92) buckets.CRITICAL += 1;
    else if (score > 0.75) buckets.HIGH += 1;
    else if (score > 0.5) buckets.MEDIUM += 1;
    else buckets.LOW += 1;
  });

  alerts.forEach((alert) => {
    const score = alert.riskScore ?? 0;
    if (score > 0.92) buckets.CRITICAL += 1;
    else if (score > 0.75) buckets.HIGH += 1;
    else if (score > 0.5) buckets.MEDIUM += 1;
    else buckets.LOW += 1;
  });

  return [
    { name: 'LOW', value: buckets.LOW, color: 'oklch(0.7 0.18 240)' },
    { name: 'MEDIUM', value: buckets.MEDIUM, color: 'oklch(0.78 0.17 75)' },
    { name: 'HIGH', value: buckets.HIGH, color: 'oklch(0.62 0.24 22)' },
    { name: 'CRITICAL', value: buckets.CRITICAL, color: 'oklch(0.72 0.19 18)' },
  ].filter((bucket) => bucket.value > 0);
}

export function buildChannelComposition(transactions: Transaction[]) {
  const channels = new Map<string, { riskSum: number; count: number }>();
  const canonical = (channel?: string) => {
    if (!channel) return 'UNKNOWN';
    const normalized = channel.toUpperCase();
    if (normalized.includes('UPI')) return 'UPI';
    if (normalized.includes('WIRE')) return 'WIRE';
    if (normalized.includes('ACH')) return 'ACH';
    if (normalized.includes('CARD') || normalized.includes('VISA') || normalized.includes('MASTERCARD')) return 'CARD';
    if (normalized.includes('SWIFT')) return 'SWIFT';
    if (normalized.includes('CRYPTO') || normalized.includes('BTC') || normalized.includes('ETH')) return 'CRYPTO';
    return normalized;
  };

  transactions.forEach((txn) => {
    const channel = canonical(txn.channel);
    const entry = channels.get(channel) ?? { riskSum: 0, count: 0 };
    entry.riskSum += txn.finalScore ?? txn.riskScore ?? 0;
    entry.count += 1;
    channels.set(channel, entry);
  });

  return Array.from(channels.entries())
    .map(([name, entry]) => ({ name, risk: +(entry.riskSum / Math.max(entry.count, 1)).toFixed(2), count: entry.count, color: name === 'UPI' ? 'oklch(0.7 0.18 240)' : name === 'CARD' ? 'oklch(0.62 0.24 22)' : name === 'SWIFT' ? 'oklch(0.78 0.17 75)' : name === 'CRYPTO' ? 'oklch(0.72 0.17 160)' : 'oklch(0.65 0.2 300)' }))
    .sort((a, b) => b.count - a.count);
}

export function buildHeatmap(transactions: Transaction[]) {
  const heat: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0));
  const counts: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0));
  transactions.forEach((txn) => {
    const d = new Date(txn.ts);
    const day = d.getDay();
    const hour = d.getHours();
    // Skip invalid timestamps that produce NaN day/hour
    if (!Number.isFinite(day) || !Number.isFinite(hour) || day < 0 || day >= 7 || hour < 0 || hour >= 24) return;
    const score = txn.finalScore ?? txn.riskScore ?? 0;
    heat[day][hour] += score;
    counts[day][hour] += 1;
  });
  return heat.map((row, day) => row.map((total, hour) => counts[day][hour] ? Math.round((total / counts[day][hour]) * 10) : 0));
}

export function buildThreatFeed(alerts: Alert[]) {
  return alerts
    .slice()
    .sort((a, b) => (b.createdAt ?? 0) - (a.createdAt ?? 0))
    .slice(0, 20)
    .map((alert) => ({
      ts: alert.createdAt ?? Date.now(),
      level: alert.priority === 'P1' ? 'critical' : alert.priority === 'P2' ? 'warning' : 'success',
      text: `${alert.priority} · ${alert.type} · ${alert.summary ?? 'Alert triggered'} · risk ${alert.riskScore.toFixed(0)}%`,
    }));
}
