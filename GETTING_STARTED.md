# Getting Started Guide

## ⚡ 5-Minute Setup

### Step 1: View Dashboards (No Setup Needed!)
```bash
cd outputs/figures/dashboards/
# Double-click any HTML file in Finder, or:
open 01_efficiency_distribution.html
```

All dashboards are self-contained HTML files. They work in any browser with no installation.

---

## 🎯 The 10 Dashboards

### 1. Efficiency Distribution
**Story:** How spread out is hospital performance?
- **X-axis:** Operational Efficiency (0-1 scale)
- **Y-axis:** Number of hospitals
- **Finding:** Most cluster 0.85-0.95

### 2. Risk Matrix
**Story:** Do efficient hospitals make money?
- **X-axis:** Operational Efficiency
- **Y-axis:** Operating Profit Margin %
- **Colors:** Hospital categories (Leader=green, Crisis=red)
- **Finding:** Leaders combine efficiency + profitability

### 3. Hospital Categories
**Story:** How many hospitals in each category?
- **LEADER:** 26 hospitals (0.6%)
- **STABILIZER:** 40,588 hospitals (70%)
- **AT-RISK:** 16,780 hospitals (29%)
- **CRITICAL:** 359 hospitals (0.6%)

### 4. Complexity vs Efficiency
**Story:** Do sicker patients hurt efficiency?
- **X-axis:** Patient Complexity Index
- **Y-axis:** Operational Efficiency
- **Finding:** Negative correlation - sicker patients = lower efficiency

### 5. Experience vs Efficiency
**Story:** Does good experience = efficiency?
- **X-axis:** Patient Experience Score (0-4)
- **Y-axis:** Operational Efficiency
- **Finding:** Positive correlation - quality = efficiency

### 6. Readmissions vs Efficiency
**Story:** Do efficient hospitals have better outcomes?
- **X-axis:** 30-Day Readmission Rate %
- **Y-axis:** Operational Efficiency
- **Finding:** Efficient hospitals have lower readmissions

### 7. Safety Net Burden
**Story:** Which hospitals serve vulnerable populations?
- **Categories:** HIGH, MODERATE, LIMITED, LOW
- **Finding:** Many hospitals carry high safety net burden

### 8. Closure Risk
**Story:** How many hospitals are in danger?
- **Risk Levels:** Low, Medium, High, Critical
- **Critical:** 359 hospitals (potential closure in 1-2 years)
- **Finding:** Policy intervention needed

### 9. Bed Size
**Story:** What's the typical hospital size?
- **Range:** 50 to 1000+ beds
- **Most Common:** 200-600 beds
- **Finding:** Larger hospitals may have scale advantages

### 10. Operating Margin
**Story:** Who's profitable?
- **Range:** -5% to +5%
- **Problem:** Many hospitals below profitability threshold
- **Finding:** Financial sustainability threatened

---

## 🔄 Regenerate Dashboards

If you want to modify the analysis or re-run:

```bash
# Step 1: Generate efficiency scores
python src/dea.py
# Output: data/processed/merged_hospital_data.parquet

# Step 2: Create dashboards
python src/visualizations.py
# Output: 10 HTML files in outputs/figures/dashboards/
```

**Time:** ~10 seconds total

---

## 📊 Understanding the Data

### Column Names

Each dashboard uses **user-friendly names**, not technical codes:

| Technical | User-Friendly | Source |
|-----------|---|---|
| `dea_efficiency` | Operational Efficiency Score | DEA-CCR Model |
| `margin` | Operating Profit Margin % | HCRIS |
| `experience_score` | Patient Experience Rating | HCAHPS |
| `all_readm_rate` | Hospital Readmission Rate % | MORTREADM |
| `clinical_risk_score` | Patient Complexity Index | Calculated |
| `hospital_stratification` | Hospital Category | Classification |

See **COLUMN_MAPPING_REFERENCE.md** for complete list.

---

## 🎨 Dashboard Features

### Every Dashboard Includes:

1. **User-Friendly Title**
   - No jargon like "dea_efficiency"
   - Clear questions like "Do sicker patients hurt efficiency?"

2. **Data Source Attribution**
   - Subtitle shows which CMS dataset
   - Example: "Data: HCRIS + DEA Analysis"

3. **Interactive Elements**
   - Hover over data points for details
   - Click legend to show/hide categories
   - Zoom & pan for detailed views
   - Camera icon to export as PNG

4. **Crisp Story**
   - Bottom of each dashboard
   - Explains key finding
   - Suggests implication

---

## 💻 System Requirements

- **Browser:** Chrome, Safari, Firefox, Edge (any modern browser)
- **No Installation Needed:** HTML files are self-contained
- **Works Offline:** No internet required after download
- **Mobile Friendly:** Works on tablets and phones

---

## 📱 Mobile & Tablet

Simply open any HTML file on your phone/tablet. Dashboards auto-resize to fit screen.

---

## 📈 Key Insights to Share

When presenting these dashboards, highlight:

1. **Only 26 leaders** (0.6%) achieve both efficiency + profitability
2. **359 hospitals at critical risk** (closure danger in 1-2 years)
3. **29% of hospitals** are at-risk and need intervention
4. **Sicker patients = lower efficiency** (safety net challenge)
5. **All data official** from CMS public reporting

---

## 🔍 Dig Deeper

### To understand calculations:
→ See **COLUMN_MAPPING_REFERENCE.md**

### To see all column definitions:
→ See **COLUMN_MAPPING_REFERENCE.md**

### To modify analysis:
→ Edit `src/visualizations.py` (well-commented code)

### To use different data:
→ Edit `src/dea.py` and re-run

---

## ❓ Troubleshooting

**Q: HTML file won't open?**
→ Try right-click → "Open With" → Choose browser

**Q: Dashboards look blank?**
→ Try different browser, or check internet connection (Plotly CDN)

**Q: Want to regenerate?**
→ Just run `python src/visualizations.py` again

**Q: Need to understand a column?**
→ See COLUMN_MAPPING_REFERENCE.md

---

## 📞 File Locations

```
outputs/figures/dashboards/
├── 01_efficiency_distribution.html
├── 02_risk_matrix.html
├── 03_hospital_categories.html
├── 04_complexity_efficiency.html
├── 05_experience_efficiency.html
├── 06_readmissions_efficiency.html
├── 07_safety_net_burden.html
├── 08_closure_risk.html
├── 09_bed_size.html
└── 10_margin_distribution.html
```

---

**All set!** Start with dashboard #1, then explore the others. 🚀
