// Centralized TypeScript models for API responses
export type Priority = "P1" | "P2" | "P3";
export type Decision = "ALLOW" | "REVIEW" | "BLOCK";
export type AlertStatus = "OPEN" | "ACK" | "ESCALATED" | "CLOSED" | "SAR_FILED";
export type SLAStatus = "OPEN" | "BREACHED" | "ESCALATED" | "RESOLVED";

export interface ModelContribution {
  model: "Behavioral" | "Sequence" | "Graph" | "Rules";
  weight: number;
  signals: string[];
}

export interface Transaction {
  id: string;
  transactionId?: string;
  ts?: number;
  timestamp?: string | number;
  createdAt?: number;
  sender: string;
  senderName?: string;
  receiver: string;
  receiverName?: string;
  amount: number;
  currency: string;
  channel?: string;
  countryFrom?: string;
  countryTo?: string;
  decision: Decision;
  riskScore: number;
  finalScore?: number;
  behaviorScore?: number;
  behavioralScore?: number;
  sequenceScore?: number;
  graphScore?: number;
  signals: string[];
  status?: string;
  ruleScore?: number;
}

export interface Alert {
  id: string;
  alertId?: string;
  priority: Priority;
  type: string;
  userId: string;
  userName?: string;
  riskScore: number;
  queue?: string;
  assignedOfficer?: string | null;
  slaDueAt?: number;
  createdAt?: number;
  status?: AlertStatus;
  caseId?: string | null;
  signals?: string[];
  finalScore?: number;
  behaviorScore?: number;
  sequenceScore?: number;
  graphScore?: number;
  reasons?: string[];
  evidence?: string[];
  amount?: number;
  channel?: string;
  summary?: string;
}

export interface Case {
  id: string;
  caseId?: string;
  priority: Priority;
  title: string;
  linkedAlerts: number;
  officer?: string | null;
  status: string;
  createdAt?: number;
  slaDueAt?: number;
  escalation?: string;
  sourceAlert?: string;
  sourceAlerts?: string[];
  evidence?: string[];
  sarStatus?: string;
}

export interface Account {
  id: string;
  name?: string;
  country?: string;
  openedAt?: number;
  createdAt?: number;
  riskTier?: string;
  riskScore?: number;
  deviceTrust?: number;
  onboardingRisk?: number;
  graphProximity?: number;
  simRisk?: number;
  vpnRisk?: number;
  suspiciousTransfers30d?: number;
  sanctionsHit?: boolean;
  pep?: boolean;
  balance?: number;
  linkedDeviceId?: string;
  lastActivity?: number;

  // onboarding detail fields
  kyc_status?: string;
  kyc_city?: string;
  created_at?: string;
  device_id?: string;
  device_model_name?: string;
  device_year?: number;
  root_status?: boolean | number;
  app_cloner_flag?: boolean | number;
  ip_address?: string;
  vpn_detected?: boolean | number;
  isp_name?: string;
  registered_imsi?: string;
  current_imsi?: string;
  sim_present?: boolean | number;
  sim_slot_count?: number;
  biometric_enabled?: boolean | number;
  onboarding_speed_ms?: number;
  identity_trust_score?: number;
  device_trust_score?: number;
  sim_binding_ok?: boolean | number;
  sim_swap_flag?: boolean | number;
  sim_age_days?: number;
  multi_sim_flag?: boolean | number;
  vpn_flag?: boolean | number;
  ip_risk_score?: number;
  device_age_years?: number;
  device_age_days?: number;
  device_shared_count?: number;
  emulator_flag?: boolean | number;
  face_match_score?: number;
  sanction_hit?: boolean | number;
  pep_hit?: boolean | number;
  typing_speed?: number;
  form_completion_time?: number;
  copy_paste_ratio?: number;
  otp_retry_count?: number;
  onboarding_risk_score?: number;
  risk_level?: string;
  graph_score?: number;
  decision?: string;
  requires_review?: boolean;
  requires_block?: boolean;
  requires_edd?: boolean;
  final_risk_score?: number;
  confidence?: number;
  officer_recommendation?: string;
  reasons?: string;
  explainability?: string[];
  suspicious_relationships?: Array<unknown>;
}

export interface GraphNode {
  id: string;
  label?: string;
  type?: string;
  role?: string;
  risk?: number;
  riskScore?: number;
  riskLevel?: string;
  x?: number;
  y?: number;
  volume?: number;
  cluster?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight?: number;
  amount?: number;
  suspicious?: boolean;
}

export interface CircularFlow {
  path: string[];
  score?: number;
  label?: string;
}

export interface ClusterSummary {
  id: number;
  name: string;
  accounts: number;
  totalRiskScore: number;
  avgRisk: number;
  hasCircularFlow?: boolean;
  color?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  circularFlows?: CircularFlow[];
  clusterSummaries?: ClusterSummary[];
  selectedAccount?: string | null;
  updatedAt?: string;
  metadata?: Record<string, unknown>;
}

export interface DashboardMetrics {
  total_transactions: number;
  blocked_transactions: number;
  review_queue: number;
  high_risk_count: number;
  cases: number;
  escalations: number;
  p1?: number;
  activeCases?: number;
  sar?: number;
  mules?: number;
  networkRisk?: number;
}

export interface QueueSnapshotItem {
  size?: number;
  oldest?: unknown;
}

export interface QueueSnapshot {
  P1_QUEUE?: QueueSnapshotItem;
  P2_QUEUE?: QueueSnapshotItem;
  P3_QUEUE?: QueueSnapshotItem;
  EDD_QUEUE?: QueueSnapshotItem;
  MANUAL_REVIEW_QUEUE?: QueueSnapshotItem;
  [key: string]: QueueSnapshotItem | undefined;
}

export interface Report {
  id: string;
  reportId?: string;
  reportType: string;
  userId?: string;
  transactionId?: string;
  decision?: string;
  finalScore?: number;
  behaviorScore?: number;
  sequenceScore?: number;
  graphScore?: number;
  ruleScore?: number;
  officerRecommendation?: string;
  immediateAction?: string;
  reason?: string;
  reasons?: string[];
  amount?: number;
  sourceEngine?: string;
  escalationLevel?: string;
  reviewStatus?: string;
  evidence?: unknown[];
  metadata?: Record<string, unknown>;
  timestamp?: number;
}

export interface Explainability {
  behavioral?: number;
  sequence?: number;
  graph?: number;
  rules?: number;
  signals?: string[];
}

export interface OfficerQueueItem { id: string; alertId?: string; assignedTo?: string; priority?: Priority; }

// (types exported above)
