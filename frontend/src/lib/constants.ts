/**
 * Application-wide constants
 * Centralized configuration for API endpoints, animation timings, and visual properties
 */

// ===== API CONFIGURATION =====
export const API_CONFIG = {
  BASE_URL: 'http://127.0.0.1:8000',
  ENDPOINTS: {
    ACCOUNTS: '/api/accounts',
  },
  TIMEOUT: 30000,
} as const;

export const API_ENDPOINTS = {
  CREATE_ACCOUNT: `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.ACCOUNTS}`,
} as const;

// ===== ANIMATION TIMING (milliseconds) =====
export const ANIMATION_TIMING = {
  METRIC_CARD_DURATION: 1200,
  METRIC_CARD_STEPS: 40,
  ZOOM_STEP: 0.2,
  ZOOM_MIN: 0.3,
  ZOOM_MAX: 2,
  DEFAULT_DELAY: 0,
} as const;

// ===== GRAPH/NETWORK VISUALIZATION =====
export const GRAPH_CONFIG = {
  NODE_SIZE: {
    MIN: 14,
    MAX: 34,
    VOLUME_DIVISOR: 280000,
  },
  CLUSTER_COLORS: {
    1: 'hsl(6, 82%, 58%)',
    2: 'hsl(32, 96%, 58%)',
    3: 'hsl(204, 88%, 60%)',
    4: 'hsl(146, 72%, 46%)',
    5: 'hsl(280, 78%, 64%)',
    6: 'hsl(172, 70%, 46%)',
  } as Record<number, string>,
  CLUSTER_GLOW: {
    1: 'rgba(244, 80, 64, 0.42)',
    2: 'rgba(255, 167, 38, 0.34)',
    3: 'rgba(64, 156, 255, 0.34)',
    4: 'rgba(46, 204, 113, 0.26)',
    5: 'rgba(168, 85, 247, 0.3)',
    6: 'rgba(20, 184, 166, 0.28)',
  } as Record<number, string>,
  RISK_COLORS: {
    high: 'hsl(0, 84%, 62%)',
    medium: 'hsl(35, 96%, 58%)',
    low: 'hsl(146, 72%, 46%)',
  },
  CLUSTER_RADIUS_MULTIPLIER: 1.18,
  CLUSTER_RY_MULTIPLIER: 0.95,
  CLUSTER_PADDING: 60,
  VIEWBOX_WIDTH: 850,
  VIEWBOX_HEIGHT: 500,
} as const;

// ===== RESPONSIVE DESIGN =====
export const BREAKPOINTS = {
  MOBILE: 768,
} as const;

// ===== TOAST NOTIFICATIONS =====
export const TOAST_CONFIG = {
  LIMIT: 1,
  REMOVE_DELAY: 1000000,
} as const;

// ===== PRIORITY LEVELS =====
export const PRIORITY_LEVELS = {
  P1: 'P1',
  P2: 'P2',
  P3: 'P3',
} as const;

// ===== RISK LEVELS =====
export const RISK_LEVELS = {
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
  INFO: 'info',
} as const;

// ===== ACCOUNT STATUS =====
export const ACCOUNT_STATUS = {
  FLAGGED: 'flagged',
  UNDER_INVESTIGATION: 'under_investigation',
  CLEARED: 'cleared',
  ESCALATED: 'escalated',
} as const;

// ===== ALERT STATUS =====
export const ALERT_STATUS = {
  OPEN: 'Open',
  UNDER_INVESTIGATION: 'Under Investigation',
  ESCALATED: 'Escalated',
  CLOSED: 'Closed',
} as const;

// ===== CLUSTER SEVERITY =====
export const CLUSTER_SEVERITY = {
  CRITICAL: 'Critical',
  HIGH: 'High',
  MEDIUM: 'Medium',
  LOW: 'Low',
} as const;

// ===== ONBOARDING RISK =====
export const ONBOARDING_RISK = {
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
} as const;

// ===== OFFICER NAMES =====
export const OFFICER_NAMES = {
  AML_OFFICER_1: 'AML Officer 1',
  AML_OFFICER_2: 'AML Officer 2',
  SENIOR_ANALYST: 'Senior Analyst',
  SYSTEM: 'System',
} as const;

// ===== TIMELINE EVENT TYPES =====
export const TIMELINE_EVENT_TYPES = {
  CREATED: 'created',
  ASSIGNED: 'assigned',
  COMMENT: 'comment',
  STATUS_CHANGE: 'status_change',
  ESCALATED: 'escalated',
} as const;

// ===== TIMELINE ICONS =====
export const TIMELINE_ICONS = {
  ALERT: '🚨',
  ASSIGN: '📌',
  COMMENT: '💬',
  CHANGE: '🔄',
  WARNING: '⚠️',
  CIRCULAR: '🔄',
} as const;

// ===== NUMERIC THRESHOLDS =====
export const THRESHOLDS = {
  HIGH_RISK_CLUSTER_AVG: 70,
  CLUSTER_MEMBERS_MIN: 0,
} as const;

// ===== CLUSTER AVERAGE RISK THRESHOLD =====
export const HIGH_RISK_CLUSTER_THRESHOLD = 70;
