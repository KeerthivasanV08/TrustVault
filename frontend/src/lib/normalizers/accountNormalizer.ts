import type { Account } from '@/types';
import { extractList } from './util';

function normalizeDate(raw: unknown): number | undefined {
  if (raw == null) return undefined;
  if (typeof raw === 'number' && !Number.isNaN(raw)) return raw;
  if (typeof raw === 'string') {
    const parsed = Date.parse(raw);
    return Number.isNaN(parsed) ? undefined : parsed;
  }
  return undefined;
}

export function normalizeAccount(raw: any): Account {
  const id = String(raw?.id ?? raw?.account_id ?? raw?.user_id ?? '');
  const openedAt = normalizeDate(raw?.openedAt ?? raw?.opened_at ?? raw?.createdAt ?? raw?.created_at) ?? Date.now();
  return {
    id,
    name: raw?.name ?? raw?.customer_name ?? raw?.account_name ?? id,
    country: raw?.country ?? raw?.country_code ?? raw?.residence_country,
    openedAt,
    createdAt: openedAt,
    riskTier: raw?.riskTier ?? raw?.risk_tier ?? raw?.riskLevel ?? raw?.risk_level ?? raw?.tier,
    riskScore: Number(raw?.riskScore ?? raw?.risk_score ?? raw?.onboarding_risk_score ?? raw?.final_risk_score ?? 0),
    deviceTrust: Number(raw?.deviceTrust ?? raw?.device_trust ?? 0),
    onboardingRisk: Number(raw?.onboardingRisk ?? raw?.onboarding_risk ?? 0),
    graphProximity: Number(raw?.graphProximity ?? raw?.graph_proximity ?? 0),
    simRisk: Number(raw?.simRisk ?? raw?.sim_risk ?? 0),
    vpnRisk: Number(raw?.vpnRisk ?? raw?.vpn_risk ?? 0),
    suspiciousTransfers30d: Number(raw?.suspiciousTransfers30d ?? raw?.suspicious_transfers_30d ?? 0),
    sanctionsHit: Boolean(raw?.sanctionsHit ?? raw?.sanctions_hit ?? false),
    pep: Boolean(raw?.pep ?? raw?.pep_hit ?? false),
    balance: raw?.balance != null ? Number(raw.balance) : undefined,
    linkedDeviceId: raw?.linkedDeviceId ?? raw?.linked_device_id,
    lastActivity: raw?.lastActivity ?? raw?.last_activity ? Number(raw.lastActivity ?? raw.last_activity) : undefined,

    kyc_status: raw?.kyc_status ?? raw?.kycStatus,
    kyc_city: raw?.kyc_city ?? raw?.kycCity,
    created_at: raw?.created_at ?? raw?.createdAt,
    device_id: raw?.device_id ?? raw?.deviceId,
    device_model_name: raw?.device_model_name ?? raw?.deviceModelName,
    device_year: Number(raw?.device_year ?? raw?.deviceYear ?? 0) || undefined,
    root_status: raw?.root_status ?? raw?.rootStatus,
    app_cloner_flag: raw?.app_cloner_flag ?? raw?.appClonerFlag,
    ip_address: raw?.ip_address ?? raw?.ipAddress,
    vpn_detected: raw?.vpn_detected ?? raw?.vpnDetected,
    isp_name: raw?.isp_name ?? raw?.ispName,
    registered_imsi: raw?.registered_imsi ?? raw?.registeredImsi,
    current_imsi: raw?.current_imsi ?? raw?.currentImsi,
    sim_present: raw?.sim_present ?? raw?.simPresent,
    sim_slot_count: Number(raw?.sim_slot_count ?? raw?.simSlotCount ?? 0) || undefined,
    biometric_enabled: raw?.biometric_enabled ?? raw?.biometricEnabled,
    onboarding_speed_ms: Number(raw?.onboarding_speed_ms ?? raw?.onboardingSpeedMs ?? 0) || undefined,
    identity_trust_score: Number(raw?.identity_trust_score ?? raw?.identityTrustScore ?? 0) || undefined,
    device_trust_score: Number(raw?.device_trust_score ?? raw?.deviceTrustScore ?? 0) || undefined,
    sim_binding_ok: Number(raw?.sim_binding_ok ?? raw?.simBindingOk ?? 0) || undefined,
    sim_swap_flag: Number(raw?.sim_swap_flag ?? raw?.simSwapFlag ?? 0) || undefined,
    sim_age_days: Number(raw?.sim_age_days ?? raw?.simAgeDays ?? 0) || undefined,
    multi_sim_flag: Number(raw?.multi_sim_flag ?? raw?.multiSimFlag ?? 0) || undefined,
    vpn_flag: Number(raw?.vpn_flag ?? raw?.vpnFlag ?? 0) || undefined,
    ip_risk_score: Number(raw?.ip_risk_score ?? raw?.ipRiskScore ?? 0) || undefined,
    device_age_years: Number(raw?.device_age_years ?? raw?.deviceAgeYears ?? 0) || undefined,
    device_age_days: Number(raw?.device_age_days ?? raw?.deviceAgeDays ?? 0) || undefined,
    device_shared_count: Number(raw?.device_shared_count ?? raw?.deviceSharedCount ?? 0) || undefined,
    emulator_flag: Number(raw?.emulator_flag ?? raw?.emulatorFlag ?? 0) || undefined,
    face_match_score: Number(raw?.face_match_score ?? raw?.faceMatchScore ?? 0) || undefined,
    sanction_hit: Number(raw?.sanction_hit ?? raw?.sanctionHit ?? 0) || undefined,
    pep_hit: Number(raw?.pep_hit ?? raw?.pepHit ?? 0) || undefined,
    typing_speed: Number(raw?.typing_speed ?? raw?.typingSpeed ?? 0) || undefined,
    form_completion_time: Number(raw?.form_completion_time ?? raw?.formCompletionTime ?? 0) || undefined,
    copy_paste_ratio: Number(raw?.copy_paste_ratio ?? raw?.copyPasteRatio ?? 0) || undefined,
    otp_retry_count: Number(raw?.otp_retry_count ?? raw?.otpRetryCount ?? 0) || undefined,
    onboarding_risk_score: Number(raw?.onboarding_risk_score ?? raw?.onboardingRiskScore ?? raw?.final_risk_score ?? 0) || undefined,
    risk_level: raw?.risk_level ?? raw?.riskLevel,
    decision: raw?.decision,
    requires_review: raw?.requires_review ?? raw?.requiresReview,
    requires_block: raw?.requires_block ?? raw?.requiresBlock,
    requires_edd: raw?.requires_edd ?? raw?.requiresEdd,
    explainability: Array.isArray(raw?.explainability) ? raw.explainability : raw?.explainability ? [String(raw.explainability)] : undefined,
    suspicious_relationships: Array.isArray(raw?.suspicious_relationships) ? raw.suspicious_relationships : undefined,
  };
}

export function extractAccounts(raw: unknown): Account[] {
  return extractList<Account>(raw).map(normalizeAccount);
}
