# Healthcare Value Frontier Analysis

Efficiency analysis of 4,572 U.S. hospitals across 15 years using Data Envelopment Analysis (DEA) and LLM-powered insights to identify cost-reduction opportunities relative to care quality.

## Problem

Healthcare systems face growing pressure to reduce costs while maintaining quality. With thousands of hospitals operating under different conditions, identifying which ones are truly efficient and which are at risk and requires requires multi-dimensional analysis beyond simple financial metrics.

## Approach

- **Data Envelopment Analysis (DEA-CCR)**: Non-parametric method to compute efficiency scores across multiple input-output dimensions (staffing, finances, patient outcomes)
- **LangChain + LLM Integration**: Automated natural language summaries and insights from complex efficiency patterns
- **Snowflake**: Cloud data warehouse for processing 57,753 hospital-year records
- **Interactive Dashboards**: 10 Plotly dashboards for exploring efficiency, risk, and closure patterns

## Key Findings

| Metric | Value |
|--------|-------|
| Hospitals Analyzed | 4,572 |
| Hospital-Years | 57,753 |
| Data Period | 2007–2021 |
| LEADER Status | 26 (0.6%) |
| AT-RISK | 16,780 (29%) |
| CRITICAL (Closure Risk) | 359 (0.6%) |

## Dashboards

| # | Dashboard | Insight |
|---|-----------|---------|
| 1 | Efficiency Distribution | Most hospitals cluster at 0.85–0.95 efficiency |
| 2 | Risk Matrix | Leaders = efficient + profitable |
| 3 | Hospital Categories | Only 26 leaders; 359 critical |
| 4 | Complexity vs Efficiency | Sicker patients correlate with lower efficiency |
| 5 | Experience vs Efficiency | Better patient experience = higher efficiency |
| 6 | Readmissions vs Efficiency | Efficient hospitals have better outcomes |
| 7 | Safety Net Burden | Many serve vulnerable populations |
| 8 | Closure Risk | 359 hospitals in danger of closing |
| 9 | Bed Size Analysis | Typical range: 200–600 beds |
| 10 | Operating Margin | Range: -5% to +5% |

## Data Sources

All data from CMS (Centers for Medicare & Medicaid Services) public reporting:
- **HCRIS** — Hospital finances and staffing
- **HCAHPS** — Patient satisfaction surveys
- **MORTREADM** — Clinical outcomes (mortality & readmissions)
- **POC** — Patient population and community data

## Tech Stack

`Python` · `Snowflake` · `LangChain` · `Plotly` · `Pandas` · `NumPy` · `DEA (Data Envelopment Analysis)`
