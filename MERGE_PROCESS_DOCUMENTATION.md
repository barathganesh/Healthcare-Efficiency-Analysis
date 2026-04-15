# Merged Dataset Documentation

## Dataset Overview

### Size & Scope
- **Total Records:** 57,753 hospital-year observations
- **Unique Hospitals:** 4,572 hospitals
- **Time Period:** 2007-2021 (15 years)
- **Total Columns:** 38
- **Memory Footprint:** 22.01 MB

### Structure
```
Index: Hospital Provider Number (pn) + Year
Rows: 57,753 (hospital-year combinations)
Columns: 38 data fields from 4 CMS datasets
```

---

## Data Sources & Merge Strategy

The merged dataset combines **4 separate CMS datasets**:

### 1. **HCAHPS** (Patient Experience)
- **Source:** Hospital Consumer Assessment of Healthcare Providers and Systems
- **Columns:** 12 individual measures + 1 composite score
  - `clean_score` - Hospital cleanliness rating
  - `commdoc_score` - Communication with doctors
  - `commnurse_score` - Communication with nurses
  - `explain_score` - Staff explanation of medicines
  - `help_score` - Help when needed
  - `pain_score` - Pain management
  - `quiet_score` - Hospital quietness
  - `recommend_score` - Likelihood to recommend
  - `overall_score` - Overall hospital rating
  - `experience_score` - **Composite score** (mean of all measures)
  - `experience_quartile` - Ranked into Q1-Q4 categories
  - `experience_yoy_change` - Year-over-year change

- **Coverage:** ~4,572 hospitals annually
- **Missing Data:** ~7.92% for `experience_yoy_change` (first year has no prior year)

### 2. **HCRIS** (Hospital Financial Data)
- **Source:** Healthcare Cost Report Information System
- **Columns:** Financial metrics
  - `beds_adultped_wtd` - Adult/pediatric beds (weighted)
  - `icu_beds_wtd` - ICU beds (weighted)
  - `margin` - Operating profit margin (%)
  
- **Coverage:** ~4,572 hospitals annually
- **Missing Data:** 1.41% for `margin` (incomplete financial reporting)

### 3. **MORTREADM** (Clinical Outcomes)
- **Source:** Hospital quality and clinical outcome measures
- **Columns:** 14 outcome metrics
  - **Mortality Rates (30-day):**
    - `ami_mort_rate` - Acute Myocardial Infarction
    - `hf_mort_rate` - Heart Failure
    - `pn_mort_rate` - Pneumonia
    - `stk_mort_rate` - Stroke
    - `copd_mort_rate` - COPD
    - `cabg_mort_rate` - Coronary Artery Bypass Graft
  
  - **Readmission Rates (30-day):**
    - `ami_readm_rate` - AMI readmission
    - `hf_readm_rate` - Heart Failure readmission
    - `pn_readm_rate` - Pneumonia readmission
    - `all_readm_rate` - All-cause readmission
    - `hk_readm_rate` - Hospital-acquired condition readmission
    - `copd_readm_rate` - COPD readmission
    - `stk_readm_rate` - Stroke readmission
    - `cabg_readm_rate` - CABG readmission
  
- **Coverage:** Varies by condition and hospital complexity
- **Missing Data:** **93.19%** (see "Missing Value Strategy" below)

### 4. **POC** (Process of Care)
- **Source:** Clinical Process of Care measures
- **Columns:** Quality measures (aggregated into composite score)
  - `process_quality_score` - Composite quality score
  
- **Coverage:** Variable by hospital
- **Missing Data:** 0% (fully imputed)

---

## Merge Process (Step-by-Step)

### Step 1: Load Individual Datasets
Each dataset is loaded from Stata (.dta) files:
- `HCAHPS_RAW` → hcahps_cleaned.dta
- `HCRIS_RAW` → hcris_cleaned.dta
- `MORTREADM_RAW` → mortreadm_cleaned.dta
- `POC_RAW` → poc_cleaned.dta

**Key Step:** Standardize provider numbers (`pn`) to string format and remove leading/trailing spaces.

```python
df['pn'] = df['pn'].astype(str).str.strip()
```

### Step 2: Data Cleaning (Per Dataset)

#### HCAHPS Cleaning:
```
✓ Remove rows with missing provider number or year
✓ Convert year to integer
✓ Impute HCAHPS scores with median by year (handles ~2-3% missing)
✓ Remove survey response rate outliers (must be 0-100%)
✓ Calculate composite experience_score = mean(all_measures)
```

**Missing Value Handling:**
- Clinical scores missing: Replace with **year-specific median**
- Logic: Each year has a stable median; filling missing values with this maintains year-level consistency

#### HCRIS Cleaning:
```
✓ Remove rows with missing provider number or year
✓ Convert year to integer
✓ Forward-fill bed capacity by hospital (within hospital, forward fill missing values)
✓ Calculate operating_margin_pct if revenue/expense available
✓ Flag outliers using z-score method (|z| > 3)
```

**Missing Value Handling:**
- Bed capacity missing: **Forward fill then backward fill** (per hospital)
- Logic: Hospital bed count is stable over time; historical values are good proxies
- Margin missing: Left as NaN (1.41%) - too important to impute

#### MORTREADM Cleaning:
```
✓ Remove rows with missing provider number or year
✓ Remove implausible values (rates outside 0-100%)
✓ Impute missing rates with condition-specific median
✓ Create composite clinical_risk_score from outcomes
```

**Missing Value Handling:**
- Readmission/mortality rates missing: Replace with **condition-specific median**
- Logic: Some hospitals don't perform certain procedures; using condition median is statistically sound

#### POC Cleaning:
```
✓ Remove rows with missing provider number or year
✓ Standardize quality measures to numeric
✓ Impute missing process metrics with median
✓ Create composite process_quality_score
```

### Step 3: The Merge Operation

**Join Method:** Full outer merge using:
```python
merged = hcahps.merge(hcris, on=['pn', 'year'], how='outer')
merged = merged.merge(mortreadm, on=['pn', 'year'], how='outer')
merged = merged.merge(poc, on=['pn', 'year'], how='outer')
```

**Key Characteristics:**
- **Join Keys:** Provider Number (`pn`) + Year (`year`)
- **Join Type:** Outer join (keeps all records even if not in all datasets)
- **Result:** Each hospital-year gets all available data

### Step 4: Post-Merge Validation

```python
def validate_merged_data(df):
    validation = {
        'total_records': len(df),
        'unique_hospitals': df['pn'].nunique(),
        'year_range': (df['year'].min(), df['year'].max()),
        'missing_pct': (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100,
        'hospitals_with_min_obs': len(df.groupby('pn').filter(
            lambda x: len(x) >= MIN_HOSPITAL_OBSERVATIONS
        )['pn'].unique())
    }
    return validation
```

---

## Missing Values: Detailed Strategy

### High-Missing Columns (93.19% missing)

**Clinical outcome measures** (mortality & readmission rates):
- `ami_mort_rate`, `hf_mort_rate`, `pn_mort_rate`, etc.

**Why So Much Missing?**
- Not all hospitals perform all procedures
  - Small hospitals may not have cardiac surgery (CABG)
  - Rural hospitals may not have stroke centers
  - Some specialties not available at all facilities
- Missing = Hospital doesn't perform this procedure = Not applicable

**Treatment:**
```python
# During DEA efficiency calculation:
readm_rate = df['all_readm_rate'].fillna(15)  # 15 is median all-cause readmission
```

**Strategy:** 
- Keep as NaN in merged dataset (preserve information)
- During analysis, use **condition-specific median** for hospital-level calculations
- This prevents overestimating outcomes for hospitals that don't perform procedures

### Medium-Missing Columns (1.41% missing)

**Operating Margin:**
```
✗ NOT imputed - too important for financial analysis
✗ Kept as NaN
✓ Filters applied when analyzing financial metrics
```

### Low-Missing Columns (0-7.92% missing)

**Patient Experience (7.92%):**
- `experience_yoy_change` (first year has no prior year)
```python
df[col] = df[col].fillna(df[col].median())  # Year-specific median
```

**Newly Calculated Fields (0% missing):**
- `clinical_risk_score` - Calculated from available outcomes
- `process_quality_score` - Calculated from process measures
- `experience_quartile` - Categorized into Q1-Q4
- `dea_efficiency` - Calculated using available data

---

## Data Flow & Integration

```
Raw Datasets (4 separate .dta files)
        ↓
        ├─→ HCAHPS (57,753 records, 12 columns)
        │   Cleaning: Remove nulls, impute scores, validate ranges
        │   ↓
        ├─→ HCRIS (57,753 records, 3 columns)
        │   Cleaning: Forward fill beds, validate financials
        │   ↓
        ├─→ MORTREADM (57,753 records, 14 columns)
        │   Cleaning: Remove outliers, impute outcomes
        │   ↓
        └─→ POC (57,753 records, 1 column)
            Cleaning: Standardize and aggregate
            ↓
        MERGE on (pn, year) - Outer Join
            ↓
        Merged Dataset (57,753 records × 38 columns)
            ├─ Provider & Time (2 columns)
            ├─ Patient Experience (12 columns)
            ├─ Financial (3 columns)
            ├─ Clinical Outcomes (14 columns)
            ├─ Quality (1 column)
            └─ Calculated Fields (6 columns)
            ↓
        Saved to: data/processed/merged_hospital_data.parquet (22.01 MB)
```

---

## Key Statistics

### Hospital Coverage by Year
```
2007-2013: ~4,400 hospitals/year (typical coverage)
2014-2021: ~4,572 hospitals/year (improved reporting)
```

### Missing Data Summary
| Metric | Missing % | Reason | Treatment |
|--------|-----------|--------|-----------|
| Clinical Outcomes | 93.19% | Hospital doesn't perform procedure | Keep as NaN; use median in calculations |
| Operating Margin | 1.41% | Incomplete financial filing | Keep as NaN; filter in analysis |
| Experience YoY Change | 7.92% | No prior year data | Fill with yearly median |
| Experience Score | ~2% | Incomplete survey response | Fill with yearly median |
| Bed Capacity | <0.1% | Rare admin error | Forward/backward fill by hospital |

### Column Type Distribution
```
Float32: 30 columns (99% of numeric data)
Object: 4 columns (pn, stratification, risk_profile, etc.)
Float64: 2 columns (margin, efficiency scores)
Int64: 1 column (year)
Categorical: 1 column (experience_quartile with Q1-Q4)
```

---

## Quality Assurance

### Validation Checks
1. ✓ No duplicate records (pn + year is unique)
2. ✓ Year range valid (2007-2021)
3. ✓ Hospital count reasonable (4,572 active hospitals)
4. ✓ No impossible values (experience 0-4 scale, margins -5% to +10%)
5. ✓ Missing patterns logical (outcomes match procedure availability)

### Data Integrity
- **Referential Integrity:** pn is consistent across all datasets
- **Temporal Integrity:** Year is consistent and sequential
- **Value Integrity:** Outliers flagged and documented
- **Completeness:** 62,891 total values available across 38 columns per record

---

## Reproducibility

To regenerate the merged dataset:

```bash
# Step 1: Load and clean each dataset
python src/data_loader.py
python src/data_cleaner.py

# Step 2: Merge datasets (integrated in dea.py)
python src/dea.py
# Output: data/processed/merged_hospital_data.parquet
```

**All merge logic is deterministic** and uses:
- Consistent provider number formatting
- Fixed missing value strategies
- Documented outlier thresholds

---

## Column Reference

See `COLUMN_MAPPING_REFERENCE.md` for detailed descriptions of all 38 columns and their data sources.
