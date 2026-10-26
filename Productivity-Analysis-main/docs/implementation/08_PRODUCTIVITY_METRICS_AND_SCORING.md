# Phase 08: Productivity Metrics and Scoring Architecture Specification

## 1. Document Overview

### 1.1 Purpose
This document specifies the operational outcome integration metrics, scoring formulas, normalization pipelines, and the four decoupled scorecards for the CCTV Workplace Productivity and Workflow Intelligence System (WBPIS). Serving **Objective D: Productivity and Output Outcomes**, this specification formally decouples camera-derived physical behavior from actual economic work output, establishing scientific rigor and legal compliance.

### 1.2 Scope
- **Metric Scope**: Canonical specifications for Metrics E1 through E6 (Throughput attainment, quality rate, timeliness rate, rework rate, quality-adjusted output, and the Output Effectiveness Score).
- **Scoring Architecture**: Formal definitions for Scorecards A, B, C, and D.
- **Governance Policy**: Strict regulatory prohibition on manufacturing arbitrary composite "employee productivity" numbers.
- **Missing-Data Rules**: Explicit enforcement of `N/A` representations; zero is never treated as a missing-data placeholder.

---

## 2. Existing Implementation Findings

Grounding assessment based on [`reports/CCTV_PRODUCTIVITY_CODEBASE_AUDIT.md`](file:///C:/Users/DELL/Desktop/cctv/reports/CCTV_PRODUCTIVITY_CODEBASE_AUDIT.md):

| Feature / Artifact | Codebase Location | Audit Status | Audit Assessment & Deficiencies |
| :--- | :--- | :--- | :--- |
| **Monolithic "Productivity Score"** | `audit_extracted/.../app.py` | `EXISTING_VERIFIED` (`ANL-01`) | Hardcoded formula: $\text{Score} = (\text{Seated Desk Time} / \text{Elapsed Time}) \times 100$. Completely conflates physical presence with work output; creates perverse incentives. |
| **Affective Psychometrics** | `video/choriwala_code.py` | `EXISTING_UNVERIFIED` | Combines facial valence, head nodding, and gaze into a composite "Engagement Index". Deemed statistically invalid and legally non-compliant. |
| **External Outcome Ingestion** | Neither codebase | `UNAVAILABLE` | Neither system possesses interfaces to ingest tickets, commits, units, or quality data from enterprise business software (Jira, SAP, Salesforce). |
| **Missing-Data Handling** | `audit_extracted/.../app.py` | `EXISTING_VERIFIED` | Replaced missing or unread camera frames with `0.0`, resulting in false $0\%$ productivity ratings during network disconnects. |

---

## 3. Four Decoupled Scorecards Architecture

To prevent unscientific conflation between physical posture and economic output, WBPIS strictly maintains **Four Independent, Unmerged Scorecards**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   FOUR INDEPENDENT SCORECARD DOMAINS                   │
├────────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────┐      ┌────────────────────────┐             │
│ │      SCORECARD A       │      │      SCORECARD B       │             │
│ │  Workflow Efficiency   │      │   Activity Analytics   │             │
│ │ (Bottleneck Risk, Dwell│      │ (Posture Distribution, │             │
│ │  Transit Churn, Choke) │      │  Interaction, Mobility)│             │
│ └────────────────────────┘      └────────────────────────┘             │
│ ┌────────────────────────┐      ┌────────────────────────┐             │
│ │      SCORECARD C       │      │      SCORECARD D       │             │
│ │  Occupancy & Presence  │      │  Output Effectiveness  │             │
│ │ (Workstation Occupancy,│      │ (Tickets, Units, Quality│            │
│ │  Utilization, Adhere)  │      │  External System Data) │             │
│ └────────────────────────┘      └────────────────────────┘             │
└────────────────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> ### The Anti-Conflation Rule
> Under no circumstances may Scorecard B (Physical Posture) or Scorecard C (Desk Occupancy) be multiplied by or combined with Scorecard D (Output) into a single "Overall Employee Productivity Score". Physical presence at a desk is an input measure of real estate utilization; it is NEVER a valid measure of knowledge worker productivity.

---

## 4. Scorecard Specifications

### 4.1 Scorecard A: Workflow Efficiency Score
Quantifies physical layout efficiency and operational smoothness across a monitored department, floor, or zone.
- **Core Formula**:
  $$\text{Bottleneck Risk} = 0.30 \cdot \text{Risk}_\text{intr} + 0.25 \cdot \text{Risk}_\text{wait} + 0.25 \cdot \text{Risk}_\text{cong} + 0.20 \cdot \text{Risk}_\text{transit}$$
  $$\text{Workflow Efficiency Score} = 100.0 - \text{Bottleneck Risk}$$
- **Normalization**: Each component risk is normalized using reference population percentiles:
  $$\text{Risk}_i = 100 \times \operatorname{clip}\left(\frac{x_i - P5_i}{P95_i - P5_i}, 0, 1\right)$$
- **Score Direction**: Higher is better ($100 = \text{Frictionless Layout}$; $0 = \text{Severe Bottlenecks}$).
- **Missing-Data Policy**: If $\ge 2$ components are missing, the score returns `N/A`. If 1 component is missing, remaining weights renormalize to sum to $1.0$.

### 4.2 Scorecard B: Activity Analytics
Provides transparent time allocations across observable physical postures without manufacturing an artificial single score:
- **Displayed Metrics**: Activity Distribution percentages (`ACT-01` to `ACT-07`), Workstation Interaction Ratio (`MET-C3`), Movement Ratio (`MET-C4`), Transition Rate (`MET-C5`), and Classification Coverage (`MET-C7`).
- **No Universal Score**: Activity states are reported as raw empirical time distributions and radar charts. No single number is generated.

### 4.3 Scorecard C: Occupancy & Presence
Evaluates physical facility and desk utilization to guide corporate real estate and space planning:
- **Displayed Metrics**: Workstation Occupancy Rate (`MET-B1`), Observed Presence Duration (`MET-B2`), Away-Time Ratio (`MET-B3`), Schedule Adherence (`MET-B4`), Occupancy Variation (`MET-B5`), and Workspace Utilization (`MET-B6`).
- **Clear Demarcation**: Labeled explicitly as "Real Estate & Utilization Analytics", never "Employee Productivity".

### 4.4 Scorecard D: Output Effectiveness
Evaluates tangible business deliverables using authenticated data ingested from external operational systems:
- **Provisional Formula**:
  $$\text{Output Score} = 0.50 \cdot \text{Throughput Score} + 0.30 \cdot \text{Quality Score} + 0.20 \cdot \text{Timeliness Score}$$
- **Mandatory External Ingestion**: Requires verified records from Jira, SAP, Salesforce, GitHub, or MES.
- **Unavailable by Default**: If no external operational data is linked to the zone or role, Scorecard D displays `UNAVAILABLE` (`N/A`). It is NEVER synthesized from video cameras.

---

## 5. Mandatory Metric Catalogue: Group E (Output & Productivity Metrics)

### Metric E1: Throughput Attainment (`MET-E1`)
1. **Metric Name & ID**: Throughput Attainment (`MET-E1`)
2. **Objective Served**: Objective D: Output & Productivity Outcomes
3. **Exact Definition**: The ratio of verified, completed work units to the role-specific expected output target over a defined operational reporting period.
4. **Mathematical Formula**:
   $$\text{Throughput Attainment}(\%) = 100 \times \frac{\text{Actual Completed Eligible Output Units}}{\text{Expected Target Output Units for Period}}$$
5. **Variables & Units**: Percentage $[0, 200]\%$; units vary by role (e.g., tickets closed, assemblies completed, claims processed).
6. **Required Source Signals**: External operational database webhook via `/api/v1/ingest/operational-outcomes`.
7. **Required Model**: Business logic ingestion engine.
8. **Aggregation Window**: Daily, weekly, or sprint cycle.
9. **Calculation Frequency**: Batch calculated upon ingestion event.
10. **Validity Conditions**: Role target must be calibrated in `dim_role_benchmarks`.
11. **Missing-Data Handling**: Returns `REQUIRES_EXTERNAL_DATA` (`N/A`) if external records are missing.
12. **Confidence Indicator**: External data validation signature / audit completeness.
13. **Score Direction**: Higher is better (Target $= 100\%$).
14. **Normalization Method**: Ratio to target with upper cap at $200\%$.
15. **Threshold Calibration**: Established by department operational planning.
16. **Interpretation**: Measures business output volume against operational plans.
17. **Known Failure Modes**: Unrecorded tasks or external system outages depressing attainment.
18. **What It Cannot Establish**: Does NOT measure task complexity or quality without Metrics E2 and E3.
19. **Database Fields**: `actual_output INT`, `target_output INT` in `fact_operational_outcomes`.
20. **API Response Fields**: `throughput_attainment_pct: float` in `/api/v1/analytics/outcomes`.
21. **Dashboard Representation**: Progress bar with target marker on Output Effectiveness panel.
22. **Validation Method**: Reconciled against enterprise ERP / ticketing audit reports.
23. **Implementation Priority**: P2.
*Status*: `REQUIRES_EXTERNAL_DATA`.

---

### Metric E2: Quality Rate (`MET-E2`)
1. **Metric Name & ID**: Quality Rate (`MET-E2`)
2. **Objective Served**: Objective D: Deliverable Standards
3. **Exact Definition**: The percentage of completed outputs that pass quality assurance inspection, peer review, or client acceptance without rejection.
4. **Mathematical Formula**:
   $$\text{Quality Rate}(\%) = 100 \times \frac{\text{Accepted Output Units}}{\text{Total Assessed Output Units}}$$
5. **Variables & Units**: Percentage $[0, 100]\%$.
6. **Required Source Signals**: Quality inspection logs, code review approvals, QA test suites.
7. **Required Model**: Business outcome parser.
8. **Aggregation Window**: Weekly or monthly rollup.
9. **Calculation Frequency**: Batch aggregation.
10. **Validity Conditions**: Minimum assessed sample size $N \ge 10\text{ units}$.
11. **Missing-Data Handling**: Returns `N/A` if sample size $< 10$.
12. **Confidence Indicator**: Ratio of assessed outputs to total outputs.
13. **Score Direction**: Higher is better (Target $\ge 98\%$).
14. **Normalization Method**: Percentage $[0, 100]\%$.
15. **Threshold Calibration**: Defined by corporate Six Sigma / QA benchmarks.
16. **Interpretation**: Measures work precision and defect-free execution.
17. **Known Failure Modes**: Delayed QA reviews causing quality score lag.
18. **What It Cannot Establish**: Cannot be observed or inferred from CCTV cameras.
19. **Database Fields**: `accepted_units INT`, `assessed_units INT` in `fact_operational_outcomes`.
20. **API Response Fields**: `quality_rate_pct: float` in `/api/v1/analytics/outcomes`.
21. **Dashboard Representation**: Radial gauge card on Output Effectiveness view.
22. **Validation Method**: Independent QA audit logs.
23. **Implementation Priority**: P2.
*Status*: `REQUIRES_EXTERNAL_DATA`.

---

### Metric E3: Timeliness Rate (`MET-E3`)
1. **Metric Name & ID**: Timeliness Rate (`MET-E3`)
2. **Objective Served**: Objective D: SLA & Deadline Adherence
3. **Exact Definition**: The percentage of completed work items delivered on or before the committed deadline or SLA target.
4. **Mathematical Formula**:
   $$\text{Timeliness Rate}(\%) = 100 \times \frac{\text{Outputs Delivered on or before Deadline}}{\text{Total Completed Outputs with Assigned Deadlines}}$$
5. **Variables & Units**: Percentage $[0, 100]\%$.
6. **Required Source Signals**: Issue tracking systems (Jira, ServiceNow, Zendesk).
7. **Required Model**: Timestamp delta parser.
8. **Aggregation Window**: Weekly or monthly sprint.
9. **Calculation Frequency**: Weekly batch aggregation.
10. **Validity Conditions**: Tasks must have explicit due dates recorded upon creation.
11. **Missing-Data Handling**: Undated tasks excluded from denominator. Returns `N/A` if no dated tasks exist.
12. **Confidence Indicator**: Data completeness ratio.
13. **Score Direction**: Higher is better (Target $\ge 95\%$).
14. **Normalization Method**: Percentage $[0, 100]\%$.
15. **Threshold Calibration**: SLA contract definitions.
16. **Interpretation**: Quantifies schedule reliability and delivery predictability.
17. **Known Failure Modes**: Retroactively modified ticket due dates distorting true timeliness.
18. **What It Cannot Establish**: Cannot be inferred from how long a worker sits at their desk.
19. **Database Fields**: `on_time_units INT`, `total_deadline_units INT` in `fact_operational_outcomes`.
20. **API Response Fields**: `timeliness_rate_pct: float` in `/api/v1/analytics/outcomes`.
21. **Dashboard Representation**: Line chart comparing committed vs. delivered dates.
22. **Validation Method**: Historical SLA compliance audits.
23. **Implementation Priority**: P2.
*Status*: `REQUIRES_EXTERNAL_DATA`.

---

### Metric E4: Rework Rate (`MET-E4`)
1. **Metric Name & ID**: Rework Rate (`MET-E4`)
2. **Objective Served**: Objective D: Waste Reduction & Operational Efficiency
3. **Exact Definition**: The percentage of completed work outputs returned by customers, QA, or downstream teams requiring corrective modification.
4. **Mathematical Formula**:
   $$\text{Rework Rate}(\%) = 100 \times \frac{\text{Outputs Requiring Rework / Reopening}}{\text{Total Assessed Outputs}}$$
5. **Variables & Units**: Percentage $[0, 100]\%$.
6. **Required Source Signals**: Defect tracking logs, bug reopen counts, customer return authorizations.
7. **Required Model**: Defect ratio calculator.
8. **Aggregation Window**: Monthly rollup.
9. **Calculation Frequency**: Monthly calculation.
10. **Validity Conditions**: Assessed outputs must be $\ge 15\text{ units}$.
11. **Missing-Data Handling**: Returns `N/A` if sample size is insufficient.
12. **Confidence Indicator**: Audit log verification score.
13. **Score Direction**: Lower is better (Zero is ideal).
14. **Normalization Method**: Percentage $[0, 100]\%$.
15. **Threshold Calibration**: Corporate target typically $< 5\%$.
16. **Interpretation**: Highlights process defects, training gaps, or unclear specifications.
17. **Known Failure Modes**: Teams closing and reopening tickets under new IDs to mask rework.
18. **What It Cannot Establish**: CCTV footage cannot detect rework events.
19. **Database Fields**: `rework_units INT` in `fact_operational_outcomes`.
20. **API Response Fields**: `rework_rate_pct: float` in `/api/v1/analytics/outcomes`.
21. **Dashboard Representation**: Amber/red warning bar on Quality card.
22. **Validation Method**: Reconciled against product return and bug reopen rates.
23. **Implementation Priority**: P3.
*Status*: `REQUIRES_EXTERNAL_DATA`.

---

### Metric E5: Quality-Adjusted Output (`MET-E5`)
1. **Metric Name & ID**: Quality-Adjusted Output (`MET-E5`)
2. **Objective Served**: Objective D: Normalized Economic Productivity
3. **Exact Definition**: The rate of defect-free, accepted work units produced per eligible working hour.
4. **Mathematical Formula**:
   $$\text{Quality-Adjusted Output} = \frac{\text{Accepted Output Units}}{\text{Eligible Working Hours}}$$
5. **Variables & Units**: Units per hour ($\text{units/hour}$).
6. **Required Source Signals**: Metric E2 (Accepted Outputs) + authorized shift hours from HR database.
7. **Required Model**: Cross-system joint ratio engine.
8. **Aggregation Window**: Monthly reporting cycle.
9. **Calculation Frequency**: Monthly calculation.
10. **Validity Conditions**: Both quality logs and authorized working hours must be present.
11. **Missing-Data Handling**: Returns `N/A` if either input is unavailable.
12. **Confidence Indicator**: Minimum confidence of constituent data sources.
13. **Score Direction**: Higher is better.
14. **Normalization Method**: Target-based normalization against historical role benchmark.
15. **Threshold Calibration**: Established per department and job grade.
16. **Interpretation**: Standard economic labor productivity metric.
17. **Known Failure Modes**: Comparing across disparate roles with non-standard task complexities.
18. **What It Cannot Establish**: Camera feeds cannot determine task units or quality acceptance.
19. **Database Fields**: `quality_adjusted_output_rate REAL` in `fact_operational_outcomes`.
20. **API Response Fields**: `quality_adjusted_output: float` in `/api/v1/analytics/outcomes`.
21. **Dashboard Representation**: Trend line chart with historical benchmark overlay.
22. **Validation Method**: Finance / Industrial Engineering labor productivity audits.
23. **Implementation Priority**: P3.
*Status*: `REQUIRES_EXTERNAL_DATA`.

---

### Metric E6: Output Effectiveness Score (`MET-E6`)
1. **Metric Name & ID**: Output Effectiveness Score (`MET-E6`)
2. **Objective Served**: Objective D: Operational Output Synthesis
3. **Exact Definition**: A weighted multi-dimensional synthesis combining normalized throughput attainment, quality rates, and timeliness rates.
4. **Mathematical Formula**:
   $$\text{Output Score} = 0.50 \cdot S_\text{throughput} + 0.30 \cdot S_\text{quality} + 0.20 \cdot S_\text{timeliness}$$
   where:
   $$S_\text{throughput} = \min(100, \text{MET-E1}), \quad S_\text{quality} = \text{MET-E2}, \quad S_\text{timeliness} = \text{MET-E3}$$
5. **Variables & Units**: Score $[0, 100]$; higher indicates stronger overall delivery.
6. **Required Source Signals**: Metrics E1, E2, and E3.
7. **Required Model**: Multi-factor synthesis engine.
8. **Aggregation Window**: Monthly sprint or reporting cycle.
9. **Calculation Frequency**: Monthly rollup.
10. **Validity Conditions**: All 3 constituent metrics must be populated from external systems.
11. **Missing-Data Handling**: If any component is missing, the score displays `UNAVAILABLE` (`N/A`). It NEVER synthesizes missing values from CCTV data.
12. **Confidence Indicator**: Joint verification of external source signatures.
13. **Score Direction**: Higher is better ($100 = \text{Flawless Execution}$).
14. **Normalization Method**: Linear bounded $[0, 100]$.
15. **Threshold Calibration**: Provisional weights ($0.50, 0.30, 0.20$) subject to organizational policy.
16. **Interpretation**: Provides leadership with a comprehensive overview of operational execution.
17. **Known Failure Modes**: Weight imbalances (e.g., heavily weighting throughput can encourage cutting corners on quality).
18. **What It Cannot Establish**: Has ZERO connection to camera video; completely independent of CCTV.
19. **Database Fields**: `output_effectiveness_score REAL` in `fact_operational_outcomes`.
20. **API Response Fields**: `output_effectiveness_score: float` in `/api/v1/analytics/outcomes`.
21. **Dashboard Representation**: Prominent KPI card on the Output Effectiveness panel.
22. **Validation Method**: Executive committee operational performance review.
23. **Implementation Priority**: P2.
*Status*: `REQUIRES_EXTERNAL_DATA`.

---

## 6. Composite Score Policy & Governance Mandate

WBPIS enforces strict governance regarding composite scoring:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   COMPOSITE SCORING GOVERNANCE POLICY                  │
├────────────────────────────────────────────────────────────────────────┤
│ ❌ PROHIBITED: "Universal Employee Productivity Score" combining       │
│    CCTV desk occupancy, posture movement, and business outputs.        │
│ ❌ PROHIBITED: Automated employee rankings, performance percentiles,   │
│    or gamified leaderboards based on behavioral surveillance.         │
│ ❌ PROHIBITED: Replacing missing data with zero (0.0). Missing data    │
│    must be rendered as `N/A` (Not Available).                          │
│                                                                        │
│ ✅ PERMITTED: Departmental Workflow Bottleneck Index (Scorecard A).    │
│ ✅ PERMITTED: Team-level physical ergonomics distribution (Scorecard B)│
│ ✅ PERMITTED: Facility-level real estate utilization (Scorecard C).    │
│ ✅ PERMITTED: Verified business output tracking (Scorecard D).         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Verification and Acceptance Criteria

| ID | Test / Acceptance Criterion | Verification Method | Pass Threshold |
| :--- | :--- | :--- | :--- |
| **AC-SCR-01** | Total decoupling of CCTV metrics from Output Effectiveness (`MET-E6`). | Code inspection & architectural AST validation. | Zero video perception features in `MET-E6` calculation |
| **AC-SCR-02** | Output metrics return `N/A` when external webhooks are unconfigured. | Unit test querying `/api/v1/analytics/outcomes` with empty DB. | All response fields return `null` / `"N/A"` |
| **AC-SCR-03** | Workflow Efficiency Score (`Scorecard A`) bounds mathematically in $[0, 100]$. | Property-based testing with 10,000 synthetic inputs. | $0.0 \le \text{Score} \le 100.0$ for all valid inputs |
| **AC-SCR-04** | Complete elimination of legacy desk-sitting "Productivity Score" (`ANL-01`). | Audit verification against legacy prototype formulas. | Desk-sitting ratio removed from productivity scoring |

---

## 8. Open Questions & Assumptions

> [!NOTE]
> ### 1. External Outcome Webhook Schema Standardization
> *Assumption*: Enterprise ticketing (Jira/ServiceNow) will post JSON payloads matching the schema in [`12_BACKEND_APIS_AND_INTEGRATION.md`](file:///C:/Users/DELL/Desktop/cctv/docs/implementation/12_BACKEND_APIS_AND_INTEGRATION.md).
> *Open Question*: Should WBPIS provide dedicated pre-built ETL connectors for Jira Cloud and GitHub, or rely on customer-built webhook forwarders?

---

## 9. Related Documentation Links

- **Workflow Bottlenecks**: Scorecard A foundation in [`07_WORKFLOW_BOTTLENECK_METRICS.md`](file:///C:/Users/DELL/Desktop/cctv/docs/implementation/07_WORKFLOW_BOTTLENECK_METRICS.md).
- **Score Calibration**: P5/P95 scaling in [`09_SCORE_CALIBRATION_AND_CONFIDENCE.md`](file:///C:/Users/DELL/Desktop/cctv/docs/implementation/09_SCORE_CALIBRATION_AND_CONFIDENCE.md).
- **Backend APIs**: Webhook schemas in [`12_BACKEND_APIS_AND_INTEGRATION.md`](file:///C:/Users/DELL/Desktop/cctv/docs/implementation/12_BACKEND_APIS_AND_INTEGRATION.md).
- **Frontend Views**: Scorecard visual specifications in [`13_FRONTEND_DASHBOARD_AND_VISUALIZATIONS.md`](file:///C:/Users/DELL/Desktop/cctv/docs/implementation/13_FRONTEND_DASHBOARD_AND_VISUALIZATIONS.md).
