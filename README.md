# TrustVault AML System
## Real-Time Anti Money Laundering Intelligence Platform

---

# 1. Introduction

TrustVault is a real-time Anti Money Laundering (AML) intelligence platform designed to simulate how modern banks and financial institutions detect suspicious onboarding activity, mule accounts, fraud networks, and laundering behavior.

This system is not just a fraud dashboard.

It is designed as a complete AML Operations Platform that combines:

- Real-time transaction monitoring
- AI/ML risk detection
- Graph-based fraud analysis
- Officer review workflows
- Alert prioritization
- Case management
- Explainability systems
- Realtime dashboards
- Live AML intelligence streaming

Current operating model:

- The Graph Explorer is driven from the live SSE transaction window and shows only the latest investigation slice.
- Neo4j is the backing graph engine for graph intelligence and health checks.
- Local settings pages are frontend preferences unless explicitly connected to a backend persistence API.

The architecture is inspired by enterprise-grade AML systems used by organizations such as:

- Feedzai
- Unit21
- Featurespace
- SEON
- BioCatch
- Sardine
- Chainalysis
- Visa Risk Manager
- Stripe Radar

---

# 2. Main Objective of the System

The platform focuses on two major AML stages:

## A. Onboarding AML Monitoring

This stage analyzes whether a user trying to create an account appears suspicious.

The system checks:

- Device integrity
- SIM binding
- VPN usage
- Emulator usage
- Face match confidence
- KYC consistency
- Sanctions and PEP checks
- Behavioral indicators during onboarding

Goal:

> Detect fake accounts, mule onboarding, synthetic identities, or risky onboarding attempts before activation.

---

## B. Post-Transaction AML Monitoring

Once an account becomes active, the system continuously monitors transactions in real time.

The platform analyzes:

- Transaction velocity
- Rapid drain behavior
- Layering patterns
- Gather-scatter movement
- Mule account routing
- Fraud network proximity
- Sequence anomalies
- Graph-based suspicious clusters

Goal:

> Detect active laundering behavior after account activation.

---

# 3. High-Level System Architecture

The complete system contains two major layers:

| Layer | Purpose |
|---|---|
| Backend | Risk detection, ML inference, alerts, orchestration |
| Frontend | AML operations console for analysts and investigators |

The system works in real time.

Transactions are continuously generated, processed, scored, prioritized, and streamed to the frontend dashboard.

---

# 4. Complete System Flow

# A. Onboarding Flow

This flow handles suspicious account creation attempts.

## Step-by-Step Flow

User Starts Registration
↓
KYC + Device + SIM + Behavioral Data Collected
↓
Context Intelligence Layer
↓
Feature Engineering
↓
Rule Engine
↓
ML Risk Scoring
↓
Decision Engine
↓
Alert Prioritization
↓
Officer Review Queue
↓
Case Creation (if needed)
↓
Final Decision

---

## Onboarding Intelligence Used

### Identity Intelligence

- Aadhaar verification
- PAN verification
- Face match score
- PEP detection
- Sanctions screening

### Device Intelligence

- Emulator detection
- Root detection
- App cloner detection
- Shared device analysis
- Device age analysis

### SIM Intelligence

- SIM binding verification
- SIM swap detection
- SIM age analysis
- Multi-SIM behavior

### Behavioral Intelligence

- Typing speed
- OTP retry behavior
- Copy-paste ratio
- Form completion speed

---

## Onboarding ML Features

The onboarding ML model uses features such as:

| Feature | Purpose |
|---|---|
| identity_trust_score | Measures KYC trustworthiness |
| device_trust_score | Measures device legitimacy |
| sim_binding_ok | SIM-device binding validation |
| sim_swap_flag | Detects SIM swap risks |
| vpn_flag | Detects anonymized traffic |
| ip_risk_score | IP reputation analysis |
| device_shared_count | Shared device intelligence |
| emulator_flag | Emulator detection |
| face_match_score | Biometric verification confidence |
| sanction_hit | Sanctions screening result |
| pep_hit | Politically exposed person detection |
| typing_speed | Behavioral typing pattern |
| copy_paste_ratio | Synthetic onboarding indicator |
| otp_retry_count | OTP abuse detection |
| behavior_risk_score | User behavior anomaly score |

---

## Onboarding Decisions

The onboarding decision engine can:

| Decision | Meaning |
|---|---|
| ALLOW | Account approved |
| REVIEW | Manual officer review required |
| BLOCK | High-risk onboarding blocked |

Additional controls:

- Enhanced Due Diligence (EDD)
- Officer escalation
- Explainability generation
- Audit logging

---

# B. Transaction Monitoring Flow

This flow continuously monitors transaction behavior after onboarding.

---

## Real-Time Transaction Pipeline

Every 2.5 seconds:

1. A realistic transaction is generated
2. Features are engineered
3. ML models evaluate the transaction
4. Decision engine calculates final risk
5. Alerts are generated
6. SSE pushes events to frontend
7. Dashboard updates live

---

## Transaction Generation

The simulator creates both:

### Normal Transactions

Examples:

- UPI payments
- Salary transfers
- Merchant purchases
- Wallet top-ups

### Suspicious Transactions

Examples:

- Rapid outbound drains
- Gather-scatter laundering
- Mule forwarding
- High velocity transfers
- Layering behavior
- Fraud rings

---

## Transaction Fields Generated

Each transaction contains:

| Field | Description |
|---|---|
| trans_id | Unique transaction ID |
| sender_id | Sender account |
| receiver_id | Receiver account |
| amount | Transaction amount |
| transaction_type | UPI/IMPS/NEFT/etc |
| channel | Mobile/Web/API |
| sender_bal_before | Sender balance before transaction |
| sender_bal_after | Sender balance after transaction |
| receiver_bal_after | Receiver balance after transaction |
| timestamp | Transaction timestamp |
| location | Geographic location |
| is_sim_bound | SIM-device validation |
| device_id | Device fingerprint |
| time_to_pay_ms | Transaction execution speed |

---

# 5. Transaction ML Architecture

The transaction system uses multiple AI/ML models together.

This is called:

> Multi-Model AML Fusion Architecture

---

## A. Behavioral ML Model

Purpose:

Detect abnormal transaction behavior.

Checks:

- Transaction velocity
- Drain ratio
- Transfer frequency
- Device anomalies
- Time-based patterns

### Example Features

| Feature | Purpose |
|---|---|
| txn_velocity_1h | Transaction count spike |
| drain_ratio | Account draining behavior |
| forwarding_delay_mins | Rapid pass-through movement |
| amount_zscore | Amount anomaly |
| device_risk | Device fraud score |

---

## B. Sequence ML Model

Purpose:

Detect temporal laundering behavior.

Analyzes:

- Last 10 transactions
- Sequential laundering flow
- Gather-scatter patterns
- Mule movement timing

The model identifies suspicious transaction sequences that normal rules may miss.

---

## C. Graph ML Model

Purpose:

Detect fraud networks and suspicious account relationships.

Current runtime note:

- The graph engine is Neo4j-backed in the backend runtime.
- The Graph Explorer in the frontend shows the latest live SSE transaction window instead of a static historical graph snapshot.

Checks:

- Fraud proximity
- Shared devices
- Shared IPs
- Mule clusters
- Network influence
- Suspicious graph communities

This simulates how real banks detect organized laundering networks.

---

# 6. Decision Engine

The platform combines:

| Component | Weight |
|---|---|
| Rules Engine | 25% |
| Behavioral ML | 30% |
| Sequence ML | 25% |
| Graph ML | 20% |

The final score determines:

| Score Range | Decision |
|---|---|
| 0.92+ | BLOCK |
| 0.70+ | REVIEW |
| 0.50+ | MONITOR |
| Below 0.50 | ALLOW |

---

# 7. Alert Prioritization System

The platform contains separate alert systems for:

- Onboarding alerts
- Transaction alerts

---

## Alert Priority Levels

| Priority | Meaning |
|---|---|
| P1 | Critical risk |
| P2 | High risk |
| P3 | Medium risk |
| INFO | Informational |

---

## Example Alert Types

### Onboarding Alerts

- Synthetic identity
- Emulator onboarding
- SIM swap onboarding
- Sanction onboarding
- PEP escalation

### Transaction Alerts

- Rapid drain
- Mule cluster
- Gather-scatter pattern
- High velocity transfers
- Layering detection

---

# 8. SLA and Escalation System

The system tracks investigation deadlines.

| Priority | SLA |
|---|---|
| P1 | 15 minutes |
| P2 | 2 hours |
| P3 | 24 hours |

If alerts exceed SLA:

- Supervisors are notified
- Escalation queues are triggered
- Officer reassignment can occur

---

# 9. Case Management System

Suspicious alerts can automatically convert into investigation cases.

Each case contains:

- Linked alerts
- Transaction evidence
- ML explainability
- Graph intelligence
- Officer notes
- Escalation history
- SAR generation status

---

# 10. Explainability System

One of the most important parts of the platform is explainability.

The system does not only say:

“Transaction is risky.”

It also explains:

WHY it is risky.

---

## Explainability Includes

### Model Contributions

- Behavioral ML contribution
- Sequence ML contribution
- Graph ML contribution
- Rule engine contribution

### Feature Importance

Examples:

- High transaction velocity
- Known mule proximity
- Rapid forwarding behavior
- Shared fraud device

### Decision Timeline

1. Rule triggered
2. Behavioral ML elevated
3. Sequence anomaly detected
4. Graph risk identified
5. Final decision blocked

---

# 11. Real-Time Frontend Dashboard

The frontend acts as a live AML operations console.

It is designed to resemble real financial crime monitoring systems.

---

# Main Frontend Pages

| Page | Purpose |
|---|---|
| Dashboard | Real-time AML monitoring overview |
| Transaction Monitor | Live transaction intelligence feed |
| Graph Explorer | Fraud network investigation |
| Alert Center | Prioritized AML alerts |
| Officer Review | Investigation workflow console |
| Case Management | Investigation tracking |
| Reports Center | SAR and AML reporting |
| Account 360° | Complete customer intelligence |
| Settings | System configuration |

---

# 12. Frontend Real-Time Features

The frontend updates live using:

- Server Sent Events (SSE)
- Zustand state management
- React Query synchronization

Realtime updates include:

- New transactions
- Alert escalation
- SLA breaches
- Officer assignments
- Graph propagation
- Dashboard metrics

---

# 13. Officer Review Workbench

This is the operational heart of the platform.

AML officers can:

- Review alerts
- Investigate suspicious accounts
- Analyze transaction timelines
- View graph intelligence
- Freeze accounts
- Escalate investigations
- Generate SAR reports
- Assign cases

---

# 14. Graph Investigation System

The graph explorer visualizes relationships between:

- Customers
- Mule accounts
- Devices
- Shared IPs
- Transaction routes
- Suspicious clusters

Analysts can click any node to:

- View profile details
- See connected fraud accounts
- Analyze ML scores
- Review transaction history

---

# 15. Reports Generated by the System

The platform supports:

| Report Type | Purpose |
|---|---|
| SAR | Suspicious Activity Report |
| STR | Suspicious Transaction Report |
| EDD | Enhanced Due Diligence |
| Mule Report | Mule account investigation |
| Network Report | Fraud cluster intelligence |
| Officer Audit | Investigator activity tracking |

---

# 16. Backend Technologies

| Technology | Purpose |
|---|---|
| FastAPI | Backend API framework |
| Pandas | Data processing |
| LightGBM | Behavioral ML |
| TensorFlow/Keras | Sequence ML |
| Graph ML | Fraud network intelligence |
| SSE | Real-time streaming |
| CSV Storage | Simulation persistence |
| Joblib | Model loading |

---

# 17. Frontend Technologies

| Technology | Purpose |
|---|---|
| React | Frontend framework |
| TypeScript | Type safety |
| Vite | Frontend tooling |
| Zustand | Real-time state management |
| React Query | Data synchronization |
| Framer Motion | Animations |
| Recharts | AML visualizations |
| Cytoscape.js | Graph investigations |
| Sonner | Realtime notifications |

---

# 18. Realtime Streaming Architecture

The platform uses:

Server Sent Events (SSE)

to stream:

- Live transactions
- Alert events
- Graph updates
- Officer assignments
- SLA breaches

This creates:

- Live AML dashboards
- Fraud war-room simulation
- Realtime investigation experience

---

# 19. Data Storage Structure

The platform currently uses structured CSV storage for simulation purposes.

Data stored includes:

- Onboarding results
- Transaction results
- Alert queues
- Officer queues
- Cases
- Explainability logs
- Reports
- SLA tracking

---

# 20. Why This System is Different

Most student AML projects only show:

- Static dashboards
- Simple fraud rules
- Basic transaction tables

TrustVault goes much deeper.

It combines:

- AI-driven risk detection
- Real-time streaming
- Graph intelligence
- Operational workflows
- Explainability systems
- Officer review tooling
- Case management
- Alert prioritization
- SLA escalation

This makes the platform behave more like a real enterprise AML operations system.

---

# 21. Final System Vision

TrustVault is designed as:

A Real-Time AML Intelligence & Operations Platform

that simulates how modern banks:

- Detect suspicious onboarding
- Monitor transactions live
- Identify mule networks
- Prioritize high-risk alerts
- Manage investigations
- Support AML officers
- Track escalations
- Generate regulatory reports

The platform combines:

Machine Learning
+
Graph Intelligence
+
Realtime Monitoring
+
Operational Workflows
+
Case Management
+
Explainability

into one unified AML ecosystem.

---

# 22. Final Outcome

By combining backend intelligence and frontend operational workflows, the system now simulates:

- Enterprise AML monitoring
- Fraud intelligence operations
- Realtime transaction surveillance
- Officer investigation workflows
- Alert management systems
- Graph-based laundering detection
- Explainable AI-driven risk scoring

The result is not just a dashboard.

It is a complete AML Operations Console.