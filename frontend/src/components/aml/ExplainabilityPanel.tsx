import { Brain, GitBranch, Network, ShieldCheck } from "lucide-react";

interface Contribution {
  model: "Behavioral" | "Sequence" | "Graph" | "Rules";
  weight: number;
  signals: string[];
}

const ICONS = {
  Behavioral: Brain,
  Sequence: GitBranch,
  Graph: Network,
  Rules: ShieldCheck,
};

const TONES = {
  Behavioral: "primary",
  Sequence: "info",
  Graph: "warning",
  Rules: "success",
} as const;

export function ExplainabilityPanel({
  contributions = defaultContribs,
  finalScore = 87,
  decision = "BLOCK",
}: { contributions?: Contribution[]; finalScore?: number; decision?: string }) {
  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Final Risk Decision</div>
          <div className="flex items-baseline gap-3 mt-1">
            <span className="text-3xl font-bold mono text-critical">{finalScore}</span>
            <span className="text-xs mono px-2 py-0.5 rounded bg-critical/15 text-critical border border-critical/40">{decision}</span>
          </div>
        </div>
        <div className="text-right text-[10px] text-muted-foreground mono">
          model-stack v3.7<br />latency 18ms
        </div>
      </div>

      <div className="space-y-2">
        {contributions.map((c) => {
          const Icon = ICONS[c.model];
          const tone = TONES[c.model];
          const toneBar = {
            primary: "bg-primary",
            info: "bg-info",
            warning: "bg-warning",
            success: "bg-success",
          }[tone];
          return (
            <div key={c.model} className="rounded-md border border-border bg-card/40 p-2.5">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="font-medium">{c.model === "Graph" ? "Neo4j Graph" : `${c.model} Model`}</span>
                </div>
                <span className="mono font-semibold">{Math.round(c.weight * 100)}%</span>
              </div>
              <div className="mt-1.5 h-1.5 rounded-full bg-muted overflow-hidden">
                <div className={`h-full ${toneBar}`} style={{ width: `${c.weight * 100}%` }} />
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {c.signals.map((s) => (
                  <span key={s} className="text-[10px] mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-1.5">Decision Timeline</div>
        <ol className="relative border-l border-border pl-4 space-y-2 text-xs">
          {[
            { t: "T+0ms", e: "Transaction ingested" },
            { t: "T+4ms", e: "Behavioral model scored 0.82" },
            { t: "T+9ms", e: "Sequence model flagged drift" },
            { t: "T+13ms", e: "Neo4j cluster CL-77 matched" },
            { t: "T+16ms", e: "Rule R-441 triggered (sub-threshold)" },
            { t: "T+18ms", e: "Decision: BLOCK → routed to P1 queue" },
          ].map((s, i) => (
            <li key={i} className="relative">
              <span className="absolute -left-[19px] top-1 h-2 w-2 rounded-full bg-primary" />
              <span className="mono text-[10px] text-muted-foreground mr-2">{s.t}</span>
              {s.e}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

const defaultContribs: Contribution[] = [
  { model: "Behavioral", weight: 0.34, signals: ["VELOCITY_SPIKE", "BEHAVIORAL_DRIFT"] },
  { model: "Sequence", weight: 0.27, signals: ["NEW_BENEFICIARY", "ROUND_AMOUNT"] },
  { model: "Graph", weight: 0.24, signals: ["NEO4J_PROXIMITY", "MULE_RING"] },
  { model: "Rules", weight: 0.15, signals: ["HIGH_RISK_CORRIDOR", "VPN_DETECTED"] },
];
