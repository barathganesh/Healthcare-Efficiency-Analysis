# Safety Net Hospital Efficiency Analysis

Healthcare efficiency analysis using Data Envelopment Analysis (DEA) on 4,572 hospitals across 15 years.

**Key Finding:** 359 hospitals at critical closure risk. Only 26 achieve LEADER status.

---

## 📁 Project Structure

```
healthcareAnalytics/
├── README.md                           ← Overview (you are here)
├── GETTING_STARTED.md                  ← Setup instructions
├── COLUMN_MAPPING_REFERENCE.md         ← Column definitions
│
├── data/
│   ├── raw/                            Original CMS datasets
│   └── processed/                      Cleaned & merged data
│
├── src/
│   ├── dea.py                          Generate efficiency scores
│   ├── visualizations.py               Create 10 dashboards
│   └── [analysis scripts]
│
├── outputs/
│   └── figures/dashboards/             10 interactive dashboards
│       ├── 01_efficiency_distribution.html
│       ├── 02_risk_matrix.html
│       ├── 03_hospital_categories.html
│       ├── 04_complexity_efficiency.html
│       ├── 05_experience_efficiency.html
│       ├── 06_readmissions_efficiency.html
│       ├── 07_safety_net_burden.html
│       ├── 08_closure_risk.html
│       ├── 09_bed_size.html
│       └── 10_margin_distribution.html
│
└── _archived_docs/                    Old documentation
```

---

## 🚀 Quick Start

### View Dashboards
```bash
cd outputs/figures/dashboards/
# Double-click any .html file or:
open 01_efficiency_distribution.html
```

### Regenerate Analysis
```bash
python src/dea.py              # ~5 sec: Generate efficiency scores
python src/visualizations.py       # ~5 sec: Create dashboards
```

---

## 📊 10 Interactive Dashboards

| # | Name | Story |
|---|------|-------|
| 1 | Efficiency Distribution | Most hospitals cluster 0.85-0.95 |
| 2 | Risk Matrix | Leaders = efficient + profitable |
| 3 | Hospital Categories | Only 26 leaders; 359 critical |
| 4 | Complexity vs Efficiency | Sicker patients = lower efficiency |
| 5 | Experience vs Efficiency | Better experience = higher efficiency |
| 6 | Readmissions vs Efficiency | Efficient = better outcomes |
| 7 | Safety Net Burden | Many serve vulnerable populations |
| 8 | Closure Risk | 359 hospitals in danger |
| 9 | Bed Size | Typical: 200-600 beds |
| 10 | Operating Margin | Range: -5% to +5% |

---

## 📈 Key Numbers

| Metric | Value |
|--------|-------|
| Hospitals Analyzed | 4,572 |
| Hospital-Years | 57,753 |
| Data Years | 2007-2021 |
| LEADER Status | 26 (0.6%) |
| AT-RISK | 16,780 (29%) |
| CRITICAL | 359 (0.6%) |

---


## 🔧 Data Sources

- **HCRIS** - Hospital finances, staffing
- **HCAHPS** - Patient satisfaction
- **MORTREADM** - Clinical outcomes
- **POC** - Patient population

All from CMS public reporting.

---
