# Data Folder Details

This document reflects the current `data/` folder at the repository root, how each subfolder is used, which CSV files live there, and which files are updated while the backend or backend-driven background tasks are running.

## Quick Meaning

The `data/` folder is not just a storage dump. In this project it acts as a hybrid datastore made of:

- static seed inputs
- offline-generated ML datasets
- live operational ledgers
- append-only audit logs
- runtime cache snapshots

Important rule:

- The frontend does not write CSV files directly.
- The backend writes or refreshes CSVs through services, startup hooks, and background realtime processing.

## Folder Map

| Folder | Main purpose |
|---|---|
| `data/raw/` | Base synthetic source data used to generate features and runtime seed data |
| `data/reference/` | Rule and reference tables used for enrichment and policy checks |
| `data/processed/` | Derived datasets, live operational snapshots, and training-ready outputs |
| `data/processed/accounts/` | Account freeze and status ledgers |
| `data/processed/alerts/` | Alert queues, SLA ledgers, escalation records, and alert-to-case state |
| `data/processed/audit/` | Audit trails for transactions, ML scores, officer actions, and explainability |
| `data/processed/cases/` | Manual officer case ledger |
| `data/processed/reports/` | SAR metadata and report artifacts |
| `data/processed/training/` | Training-time feature outputs used by model pipelines |
| `data/processed/runtime/` | Runtime state snapshots used by in-memory services |
| `data/processed/explainability/` | Explainability exports and supporting artifacts |

## `data/raw/`

These are the base inputs. Most of them are generated offline by scripts, but one of them is also refreshed at runtime by the realtime engine.

| File | What it stores | When it is used | Updated while backend is running? |
|---|---|---|---|
| `users.csv` | Synthetic customer onboarding source records such as device, SIM, KYC, IP, and behavioral seed attributes | Used by `user_features.py`, `generate_onboarding_results.py`, `load_to_neo4j.py`, `AccountService`, and other onboarding context services | Usually no. It is treated as a seed file |
| `transactions.csv` | Synthetic transaction source data with sender, receiver, amount, timestamp, and balance fields | Used by `generate_data.py`, `transaction_features.py`, `user_velocity.py`, `create_labels.py`, `build_final_dataset.py`, `train_sequence_model.py`, and `ContextService` fallback logic | Yes, in the realtime path. `VelocityService.update_after_transaction()` appends every realtime transaction and rewrites this file |
| `device_age_reference.csv` | Device age / model reference data | Used by `generate_data.py` and `user_features.py` to enrich device risk and age signals | No in current code |

### Notes on `raw/`

- `transactions.csv` is the only raw seed file that is also refreshed live.
- The live refresh happens only in the realtime engine path, not as a timed batch job.
- When there is no live traffic yet, fallback logic can still read this folder to seed runtime snapshots.

## `data/reference/`

These files are reference and policy inputs. They are not model outputs.

| File | What it stores | When it is used | Updated while backend is running? |
|---|---|---|---|
| `ip_risk_reference.csv` | IP reputation, city, ASN, VPN/proxy/hosting flags | Used by `generate_data.py`, `user_features.py`, and onboarding enrichment services | No in current code |
| `sanction_list.csv` | Sanctions reference list | Used by `user_features.py` and onboarding screening logic | No in current code |
| `policy_rules.json` | Policy thresholds and control rules | Used by control/policy engine logic for limits and AML rules | Usually static |
| `whitelist.csv` | Officer-managed whitelist reference file | Written by `WhitelistOverrideService` when a manual override is added | Yes, if an officer adds an override through the backend |

### Important whitelist caveat

There are two whitelist files in the tree:

- `data/reference/whitelist.csv` is the officer override/source file.
- `data/processed/whitelist.csv` is the file read by `WhitelistService` for transaction bypass checks.

That means the current codebase has a sync gap: adding a row to the reference whitelist does not automatically update the processed whitelist reader unless another sync step is run.

## `data/processed/`

This is the main working area. It contains generated ML datasets, runtime snapshots, and operational state.

### Root files in `data/processed/`

| File | What it stores | Created by / updated by | Used by |
|---|---|---|---|
| `user_features.csv` | One row per user with onboarding and device/network risk features | Offline `user_features.py`; read at runtime by `AccountService`, `ContextService`, and transaction control logic | Onboarding scoring, account views, transaction control, training pipelines |
| `transaction_features.csv` | Transaction-level feature engineering output | Offline `transaction_features.py` | Label generation, final dataset build, training, analytics |
| `graph_features.csv` | Graph topology features such as fraud neighbors and mule cluster size | Offline `graph_features.py` using Neo4j intelligence | Label generation, onboarding results, final dataset build, account context, graph analytics |
| `labels.csv` | Synthetic ground-truth labels for mule, bot, synthetic identity, and ATO style outcomes | Offline `create_labels.py` | Final dataset build, onboarding results, training, evaluation |
| `final_dataset.csv` | Main training dataset that merges raw transactions with user, graph, velocity, onboarding, and label layers | Offline `build_final_dataset.py` | Behavioral model training, sequence model training, downstream analytics |
| `user_velocity.csv` | Rolling velocity metrics per user such as 24h sum, transaction count, drain ratio, and last update time | Offline `user_velocity.py`; also rewritten live by `VelocityService.update_after_transaction()` | Transaction control engine, context service, behavioral inference, runtime refresh |
| `onboarding_results.csv` | Offline onboarding intelligence snapshot with final risk score, risk level, decision, review flags, and reasons | Offline `generate_onboarding_results.py` | `AccountService`, `ContextService`, onboarding analytics, training inputs |
| `recent_transactions.csv` | Live snapshot of the latest transactions visible to the runtime context service | Written by `ContextService` when `LIVE_TRANSACTIONS` has data; seeded from fallbacks if empty | Transaction context lookup, UI recent activity, transaction sequence evaluation |
| `sim_registry.csv` | SIM binding ledger with user, IMSI, device, and trust metadata | Initialized by `init_ledgers.py`; read by `SimBindingService` | SIM binding verification, onboarding/device checks |
| `whitelist.csv` | Processed whitelist lookup table | Read by `WhitelistService` | Transaction bypass checks |
| `control_decisions.csv` | Control engine decisions and metadata | Written by `app/db/file_storage.py` and related logging calls | Audit, reporting, control review |
| `ml_training_dataset.csv` | Training snapshot present in the tree | No active writer was found in the inspected code | Likely legacy or alternate training export |
| `officer_cases.csv` | Legacy or duplicate case snapshot present in the root of `processed/` | No current writer was found in the inspected code | Likely legacy or alternate case export |

### Update behavior for root `processed/` files

- `user_features.csv`, `transaction_features.csv`, `graph_features.csv`, `labels.csv`, and `final_dataset.csv` are batch/offline outputs.
- `user_velocity.csv` is both batch-generated and live-refreshed.
- `recent_transactions.csv` is a runtime cache snapshot, not the canonical transaction source.
- `onboarding_results.csv` in the root `processed/` folder is the offline merged onboarding dataset. The runtime onboarding audit log uses a separate file under `data/processed/audit/onboarding_decisions.csv`.

## `data/processed/alerts/`

These files hold the live operational alert and queue ledgers. They are append-heavy and are updated during both onboarding and transaction processing.

| File | What it stores | When it is updated | Used by |
|---|---|---|---|
| `onboarding_alerts.csv` | Alerts created from risky onboarding decisions | Written whenever onboarding risk triggers alert creation | Onboarding alert views, officer queue, case conversion |
| `transaction_alerts.csv` | Alerts created from risky transaction decisions | Written whenever a transaction is scored as high risk or requires review | Alert dashboards, officer workflow, escalation |
| `officer_queue.csv` | Snapshot rows showing officer assignment state, count, and last assignment time | Appended each time an alert is enqueued or officer workload is persisted | Officer queue views, workload tracking |
| `case_registry.csv` | Auto-converted investigation cases from alerts | Written when alerts convert to cases or when case API snapshots are appended | Case management, officer review, SAR/STR workflow |
| `sla_tracking.csv` | Alert SLA records with due time and breach state | Written when a new alert gets an SLA record | SLA monitoring, escalation |
| `escalation_log.csv` | Escalation history when an SLA breach or escalation event occurs | Written when escalation checks detect a breach | Supervisor review, audit |

### How alert files are used together

1. A risky onboarding or transaction event creates an alert.
2. Priority is assigned.
3. An officer queue snapshot is appended.
4. An SLA row is created.
5. If the alert converts into a case, a `case_registry.csv` row is added.
6. If the SLA is breached, an escalation row is appended.

## `data/processed/audit/`

These are append-only compliance and traceability logs.

| File | What it stores | Updated by | Used by |
|---|---|---|---|
| `transaction_audit.csv` | Transaction decision trail with score, priority, reasons, and rule hits | `AuditService.log_transaction_decision()` and `log_all()` | Investigation traceability, reporting, audit review |
| `ml_audit.csv` | ML score trail for behavior, sequence, graph, and final scores | `AuditService.log_ml_scores()` and `log_all()` | Model transparency, scoring review |
| `officer_audit.csv` | Officer actions such as assign, freeze, close, or review | `AuditService.log_officer_action()` | Officer accountability, compliance |
| `explainability_audit.csv` | Explainability findings and evidence | `AuditService.log_explainability_event()` and reporting logic | Explainability reports, audit review |
| `onboarding_decisions.csv` | Runtime onboarding audit log used by onboarding explanation endpoints | `OnboardingAuditService.log()` | Onboarding explanation, audit history |

### Audit update behavior

- These files are append-only.
- They are written on each relevant event, not on a schedule.
- `OnboardingAuditService` uses a lock to avoid concurrent write collisions.

## `data/processed/cases/`

| File | What it stores | Updated by | Used by |
|---|---|---|---|
| `case_registry.csv` | Canonical case ledger with case status and assignment | `CaseRepository.upsert_case()` through officer and alert case flows | Manual case management, officer follow-up, case retrieval |

### Note

This is separate from `data/processed/alerts/case_registry.csv`.

- `alerts/case_registry.csv` is alert-driven auto-conversion state.
- `cases/case_registry.csv` is the canonical case workspace.

## `data/processed/reports/`

| File | What it stores | Updated by | Used by |
|---|---|---|---|
| `sar_metadata.csv` | SAR report metadata including generated file name, filing type, status, and runtime session | `SARGenerationService` | SAR generation, filing workflow, report tracking |

## `data/processed/accounts/`

| File | What it stores | Updated by | Used by |
|---|---|---|---|
| `freeze_registry.csv` | Account freeze and unfreeze history | `AccountOperationsService.freeze_account()` and related status methods | Account status checks, freeze workflows |

## Files That Update While the Backend Runs

Yes, several CSV files are updated while the backend is running.

### 1. Realtime transaction cycle

The realtime engine starts during FastAPI startup:

- `main.py` calls `start_realtime_engine_once()` inside the app lifespan, which creates the background task for `start_realtime_engine()`.
- The realtime loop runs every `2.5` seconds.
- Each loop generates a transaction, processes it, scores it, publishes it to SSE, and updates in-memory state.

Files affected by that path:

- `data/raw/transactions.csv` is appended through `VelocityService.update_after_transaction()`
- `data/processed/user_velocity.csv` is recomputed and rewritten
- `data/processed/recent_transactions.csv` is refreshed from the live transaction deque when the context service loads or ensures the live snapshot
- `data/processed/alerts/transaction_alerts.csv` is appended for risky transactions
- `data/processed/alerts/officer_queue.csv` is appended with officer assignment snapshots
- `data/processed/alerts/sla_tracking.csv` is appended when SLA records are created
- `data/processed/alerts/case_registry.csv` is appended when alerts auto-convert to cases
- `data/processed/audit/transaction_audit.csv`, `ml_audit.csv`, and `explainability_audit.csv` are appended through audit/reporting flows

### 2. Manual transaction API cycle

When a user or frontend calls `POST /api/transactions` or `POST /api/transactions/analyze`:

- the transaction is scored by the manual transaction service
- audit and reporting rows are written
- transaction or onboarding alerts may be created
- graph and report records may be persisted

Files commonly affected:

- `data/processed/control_decisions.csv`
- `data/processed/reports/sar_metadata.csv`
- `data/processed/audit/explainability_audit.csv`
- `data/processed/alerts/transaction_alerts.csv`
- `data/processed/alerts/sla_tracking.csv`
- `data/processed/alerts/officer_queue.csv`
- `data/processed/alerts/case_registry.csv`
- `data/processed/audit/*.csv`

### 3. Manual onboarding API cycle

When a user or frontend calls `POST /api/onboarding/onboarding` or `POST /api/onboarding/evaluate`:

- onboarding context is built from reference and processed CSVs
- the onboarding result is written to the runtime audit onboarding log
- risky onboarding outcomes can create onboarding alerts

Files commonly affected:

- `data/processed/audit/onboarding_decisions.csv`
- `data/processed/alerts/onboarding_alerts.csv`
- `data/processed/alerts/officer_queue.csv`
- `data/processed/alerts/sla_tracking.csv`
- `data/processed/alerts/case_registry.csv`

### 4. Officer and case actions

When officers add cases, assign cases, freeze users, or add whitelist overrides:

- `data/processed/cases/case_registry.csv` can be created or updated
- `data/processed/accounts/freeze_registry.csv` can be created or updated
- `data/reference/whitelist.csv` can receive new whitelist rows
- audit logs can receive officer action rows

## What Gets Updated Inside the Rows

### `user_velocity.csv`

Updated attributes:

- `rolling_24h_sum`
- `txn_count_24h`
- `drain_ratio`
- `unique_counterparties_24h`
- `round_number_ratio`
- `near_threshold_count`
- `avg_holding_time_mins`
- `velocity_gradient`
- `last_updated`

Why it matters:

- feeds the control engine
- feeds the transaction context service
- feeds behavioral and sequence risk scoring

### `recent_transactions.csv`

This is a live cache snapshot. It stores the latest transaction payloads used by the UI and by sequence/context lookups.

Why it matters:

- the transaction sequence model needs recent history
- the frontend recent activity view needs current data
- runtime context services need a fast local snapshot

### Alert and case ledgers

The alert files store:

- alert IDs
- priority and severity
- risk scores
- assigned officers and queues
- SLA due times
- escalation state
- case conversion state

Why it matters:

- supports analyst workflow
- drives SLA monitoring
- supports investigations, reviews, and escalations

### Audit files

The audit files store:

- score outputs
- decisions
- reasons and rule hits
- explainability evidence
- officer actions

Why it matters:

- compliance and traceability
- reporting and investigation
- explanation for why a transaction or onboarding event was flagged

## Tech Used For Auto-Update

The auto-update behavior is achieved with a small set of backend technologies, not a separate job scheduler.

| Technology | Role |
|---|---|
| FastAPI lifespan startup | Initializes storage directories and starts the realtime background engine |
| `start_realtime_engine_once()` | Creates the realtime engine background task once during startup |
| `asyncio.sleep(2.5)` loop | Provides the fixed realtime generation cadence |
| `deque` in memory | Stores live transactions and alerts for quick access and SSE streaming |
| SSE / `EventSourceResponse` | Streams live transaction and alert events to the frontend |
| `pandas.read_csv()` / `to_csv()` | Reads and writes the CSV-backed store |
| `safe_to_csv()` / `safe_append_csv()` | Safer file writes used by some services |
| `threading.Lock` | Prevents concurrent write collisions in onboarding audit logging |
| `Path.mkdir(parents=True, exist_ok=True)` | Ensures data directories exist before writes |

### What is not used

The current codebase does not rely on:

- APScheduler
- cron jobs
- file watchers
- Celery-style background workers

## Practical Reading Order

If you want to understand the folder quickly, read it in this order:

1. `data/raw/transactions.csv` and `data/raw/users.csv`
2. `data/reference/policy_rules.json` and `data/reference/ip_risk_reference.csv`
3. `data/processed/user_features.csv`, `user_velocity.csv`, and `onboarding_results.csv`
4. `data/processed/final_dataset.csv`
5. `data/processed/alerts/*`
6. `data/processed/audit/*`

## Important Caveats

- `data/raw/transactions.csv` is both a seed dataset and a live append target in the realtime path.
- `data/processed/recent_transactions.csv` is a derived cache, not the source of truth.
- `data/processed/officer_cases.csv` and `data/processed/ml_training_dataset.csv` still exist as legacy or duplicate snapshots, but no active writer was found in the inspected backend code.
- `data/processed/onboarding_results.csv` is the offline merged dataset, while `data/processed/audit/onboarding_decisions.csv` is the runtime audit log used by onboarding explanation flows.

## Summary

In short, the `data/` folder serves four roles at once:

- seed data for offline generation
- reference data for risk rules
- live runtime ledgers for alerts, cases, audits, and account state
- cached snapshots for fast API and frontend access

The live update mechanism is event-driven and background-based, with the realtime engine refreshing data every 2.5 seconds and individual services appending audit, alert, case, SAR, or freeze rows whenever a transaction, onboarding event, or officer action occurs.