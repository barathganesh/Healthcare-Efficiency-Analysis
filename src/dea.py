"""Hospital Efficiency Scoring & Safety Net Analysis (DEA-CCR Model)

Merges all 4 CMS datasets using overlapping years (2007-2021),
performs DEA efficiency analysis, and generates safety net insights.
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("=" * 80)
print("SAFETY NET HOSPITAL EFFICIENCY ANALYSIS")
print("=" * 80)

# ============================================================================
# STEP 1: Load & Merge All 4 Datasets (Overlapping Years, Outer Join)
# ============================================================================
print("\n📥 STEP 1: Loading raw datasets...")

hcris = pd.read_stata('data/raw/hcris.dta')
hcahps = pd.read_stata('data/raw/hcahps.dta')
mortreadm = pd.read_stata('data/raw/mortreadm.dta')
poc = pd.read_stata('data/raw/poc.dta')

print(f"  HCRIS:     {len(hcris):>8,} records × {len(hcris.columns):>3} cols  (Years: {int(hcris['year'].min())}-{int(hcris['year'].max())})")
print(f"  HCAHPS:    {len(hcahps):>8,} records × {len(hcahps.columns):>3} cols  (Years: {int(hcahps['year'].min())}-{int(hcahps['year'].max())})")
print(f"  MORTREADM: {len(mortreadm):>8,} records × {len(mortreadm.columns):>3} cols  (Years: {int(mortreadm['year'].min())}-{int(mortreadm['year'].max())})")
print(f"  POC:       {len(poc):>8,} records × {len(poc.columns):>3} cols  (Years: {int(poc['year'].min())}-{int(poc['year'].max())})")

# Find overlapping years across all 4 datasets
overlap_years = sorted(
    set(hcris['year']) & set(hcahps['year']) & set(mortreadm['year']) & set(poc['year'])
)
print(f"\n  Overlapping years: {overlap_years[0]}-{overlap_years[-1]} ({len(overlap_years)} years)")

# Filter to overlapping years only
hcris = hcris[hcris['year'].isin(overlap_years)]
hcahps = hcahps[hcahps['year'].isin(overlap_years)]
mortreadm = mortreadm[mortreadm['year'].isin(overlap_years)]
poc = poc[poc['year'].isin(overlap_years)]

# Standardize provider number format
for df in [hcris, hcahps, mortreadm, poc]:
    df['pn'] = df['pn'].astype(str).str.strip()

# Outer merge on (pn, year)
print("\n🔗 Merging datasets (outer join on provider + year)...")
merged = hcris.merge(hcahps, on=['pn', 'year'], how='outer')
print(f"  HCRIS + HCAHPS:      {len(merged):,} records")
merged = merged.merge(mortreadm, on=['pn', 'year'], how='outer')
print(f"  + MORTREADM:         {len(merged):,} records")
merged = merged.merge(poc, on=['pn', 'year'], how='outer')
print(f"  + POC:               {len(merged):,} records")

print(f"\n  ✅ MERGED DATASET: {len(merged):,} records × {len(merged.columns)} columns")
print(f"     Unique hospitals: {merged['pn'].nunique():,}")
print(f"     Year range: {int(merged['year'].min())}-{int(merged['year'].max())}")

# ============================================================================
# STEP 2: Create Key Derived Variables for Safety Net Analysis
# ============================================================================
print("\n📊 STEP 2: Engineering features for safety net analysis...")

# --- Patient Experience Composite Score ---
experience_cols = ['clean_score', 'commdoc_score', 'commnurse_score', 'explain_score',
                   'help_score', 'overall_score', 'pain_score', 'quiet_score',
                   'recommend_score']
avail_exp_cols = [c for c in experience_cols if c in merged.columns]
merged['experience_score'] = merged[avail_exp_cols].mean(axis=1)
print(f"  ✓ Experience score (from {len(avail_exp_cols)} HCAHPS dimensions)")

# --- Medicaid Burden (proxy for safety net status) ---
if 'ipdischarges_medicaid' in merged.columns and 'ipdischarges_adultped' in merged.columns:
    merged['medicaid_share'] = (
        merged['ipdischarges_medicaid'] / merged['ipdischarges_adultped'].replace(0, np.nan)
    )
    print(f"  ✓ Medicaid share (discharges)")

# --- Uncompensated Care Burden ---
if 'uccare_cost_harmonized' in merged.columns and 'netpatrev' in merged.columns:
    merged['uccare_burden'] = (
        merged['uccare_cost_harmonized'] / merged['netpatrev'].replace(0, np.nan)
    )
    print(f"  ✓ Uncompensated care burden")

# --- Case Mix Index ---
if 'tacmiv' in merged.columns:
    print(f"  ✓ Case-mix index (tacmiv) available")

# --- Bed Utilization ---
if 'ipbeddays_adultped' in merged.columns and 'availbeddays_adultped' in merged.columns:
    merged['bed_occupancy_rate'] = (
        merged['ipbeddays_adultped'] / merged['availbeddays_adultped'].replace(0, np.nan)
    )
    print(f"  ✓ Bed occupancy rate")

# --- Cost Efficiency ---
if 'totcost' in merged.columns and 'ipdischarges_adultped' in merged.columns:
    merged['cost_per_discharge'] = (
        merged['totcost'] / merged['ipdischarges_adultped'].replace(0, np.nan)
    )
    print(f"  ✓ Cost per discharge")

# --- FTE per Bed ---
if 'fte_employee_payroll_wtd' in merged.columns and 'beds_total_wtd' in merged.columns:
    merged['fte_per_bed'] = (
        merged['fte_employee_payroll_wtd'] / merged['beds_total_wtd'].replace(0, np.nan)
    )
    print(f"  ✓ FTE per bed")

# --- Teaching Intensity ---
if 'fte_intern_resident_wtd' in merged.columns and 'beds_total_wtd' in merged.columns:
    merged['teaching_intensity'] = (
        merged['fte_intern_resident_wtd'] / merged['beds_total_wtd'].replace(0, np.nan)
    )
    print(f"  ✓ Teaching intensity")

# ============================================================================
# STEP 3: DEA Efficiency Scoring
# ============================================================================
print("\n⚙️ STEP 3: Calculating DEA efficiency scores...")

def calc_efficiency(row):
    """DEA-CCR inspired efficiency: weighted outputs / weighted inputs"""
    # INPUTS (resources consumed)
    beds = row.get('beds_adultped_wtd', np.nan)
    beds = beds if pd.notna(beds) and beds > 0 else 300

    cost = row.get('totcost', np.nan)
    cost = cost if pd.notna(cost) and cost > 0 else 50_000_000

    inp_beds = min(beds / 1000, 1.0) * 0.4
    inp_cost = min(cost / 500_000_000, 1.0) * 0.3
    inp = inp_beds + inp_cost + 0.3  # baseline
    inp = np.clip(inp, 0.1, 1.0)

    # OUTPUTS (results achieved)
    exp = row.get('experience_score', np.nan)
    exp = exp if pd.notna(exp) else 2.5

    readm = row.get('all_readm_rate', np.nan)
    readm = readm if pd.notna(readm) else 15.0

    marg = row.get('margin', np.nan)
    marg = marg if pd.notna(marg) else 0.0

    exp_c = min(exp / 4.0, 1.0) * 0.35
    qual_c = (1 - min(readm / 25, 1.0)) * 0.35
    fin_c = min((marg + 0.5) / 1.0, 1.0) * 0.30

    out = exp_c + qual_c + fin_c
    out = np.clip(out, 0, 1.0)

    eff = out / inp if inp > 0 else 0.5
    return np.clip(eff, 0, 1.0)

merged['dea_efficiency'] = merged.apply(calc_efficiency, axis=1)
print(f"  ✓ Efficiency scores (mean: {merged['dea_efficiency'].mean():.3f}, "
      f"median: {merged['dea_efficiency'].median():.3f})")

# ============================================================================
# STEP 4: Safety Net Hospital Classification
# ============================================================================
print("\n🏥 STEP 4: Classifying safety net hospitals...")

def classify_safety_net(row):
    """
    Safety net classification based on:
    1. Medicaid share of discharges (primary indicator)
    2. Uncompensated care burden
    3. Patient experience (proxy for underserved populations)
    """
    score = 0

    # Medicaid share (strongest signal)
    med_share = row.get('medicaid_share', np.nan)
    if pd.notna(med_share):
        if med_share >= 0.30:
            score += 3
        elif med_share >= 0.20:
            score += 2
        elif med_share >= 0.10:
            score += 1

    # Uncompensated care burden
    uccare = row.get('uccare_burden', np.nan)
    if pd.notna(uccare):
        if uccare >= 0.10:
            score += 3
        elif uccare >= 0.05:
            score += 2
        elif uccare >= 0.02:
            score += 1

    # Low patient experience (often correlated with under-resourced hospitals)
    exp = row.get('experience_score', np.nan)
    if pd.notna(exp):
        if exp < 2.3:
            score += 2
        elif exp < 2.7:
            score += 1

    if score >= 5:
        return 'HIGH'
    elif score >= 3:
        return 'MODERATE'
    elif score >= 1:
        return 'LIMITED'
    else:
        return 'LOW'

merged['safety_net_category'] = merged.apply(classify_safety_net, axis=1)
sn_counts = merged['safety_net_category'].value_counts()
print(f"  Safety Net Distribution:")
for cat in ['HIGH', 'MODERATE', 'LIMITED', 'LOW']:
    if cat in sn_counts.index:
        print(f"    {cat:>10}: {sn_counts[cat]:>6,} ({sn_counts[cat]/len(merged)*100:.1f}%)")

# ============================================================================
# STEP 5: Hospital Stratification
# ============================================================================
print("\n📋 STEP 5: Stratifying hospitals...")

def stratify(row):
    eff = row['dea_efficiency']
    marg = row.get('margin', np.nan)
    marg = marg if pd.notna(marg) else 0
    if eff >= 0.85 and marg > 0.05:
        return 'LEADER'
    elif eff >= 0.70 and marg > -0.05:
        return 'STABILIZER'
    elif eff >= 0.55:
        return 'AT-RISK'
    else:
        return 'CRITICAL'

merged['hospital_stratification'] = merged.apply(stratify, axis=1)
strat_counts = merged['hospital_stratification'].value_counts()
print(f"  Stratification:")
for cat in ['LEADER', 'STABILIZER', 'AT-RISK', 'CRITICAL']:
    if cat in strat_counts.index:
        print(f"    {cat:>12}: {strat_counts[cat]:>6,} ({strat_counts[cat]/len(merged)*100:.1f}%)")

# ============================================================================
# STEP 6: Clinical Risk Score
# ============================================================================
print("\n🩺 STEP 6: Calculating clinical risk...")

merged['clinical_risk_score'] = (
    (merged['all_readm_rate'].fillna(15) / 20.0) * 0.4 +
    ((4 - merged['experience_score'].fillna(2.5)) / 4) * 0.3 +
    ((merged['beds_adultped_wtd'].fillna(300) / 1000) * 0.3)
)
merged['clinical_risk_score'] = np.clip(merged['clinical_risk_score'], 0, 1.0)
print(f"  ✓ Clinical risk (mean: {merged['clinical_risk_score'].mean():.3f})")

# ============================================================================
# STEP 7: Closure Risk Assessment
# ============================================================================
print("\n⚠️ STEP 7: Assessing closure risk...")

def total_risk(row):
    # Operational risk (low efficiency)
    op_r = (1 - row['dea_efficiency']) * 25

    # Financial risk (negative margins)
    marg = row.get('margin', np.nan)
    marg = marg if pd.notna(marg) else 0
    if marg < -0.10:
        fin_r = 25
    elif marg < -0.05:
        fin_r = 20
    elif marg < 0:
        fin_r = 15
    elif marg < 0.02:
        fin_r = 10
    else:
        fin_r = 5

    # Readmission risk
    readm = row.get('all_readm_rate', np.nan)
    readm = readm if pd.notna(readm) else 15
    if readm > 18:
        pat_r = 20
    elif readm > 16:
        pat_r = 12
    else:
        pat_r = 5

    # Safety net burden risk
    sn = row.get('safety_net_category', 'LOW')
    sn_map = {'HIGH': 15, 'MODERATE': 10, 'LIMITED': 5, 'LOW': 2}
    sn_r = sn_map.get(sn, 5)

    # Experience risk
    exp = row.get('experience_score', np.nan)
    exp = exp if pd.notna(exp) else 3.0
    if exp < 2.3:
        exp_r = 15
    elif exp < 2.7:
        exp_r = 8
    else:
        exp_r = 2

    total = op_r + fin_r + pat_r + sn_r + exp_r
    return np.clip(total, 0, 100)

merged['total_risk'] = merged.apply(total_risk, axis=1)

def risk_profile(score):
    if score >= 70:
        return 'CRITICAL'
    elif score >= 50:
        return 'HIGH'
    elif score >= 30:
        return 'MEDIUM'
    else:
        return 'LOW'

merged['risk_profile'] = merged['total_risk'].apply(risk_profile)
risk_counts = merged['risk_profile'].value_counts()
print(f"  Closure Risk:")
for cat in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
    if cat in risk_counts.index:
        print(f"    {cat:>10}: {risk_counts[cat]:>6,} ({risk_counts[cat]/len(merged)*100:.1f}%)")

# ============================================================================
# STEP 8: Save Results
# ============================================================================
print("\n💾 STEP 8: Saving results...")

Path('data/processed').mkdir(parents=True, exist_ok=True)
merged.to_parquet('data/processed/merged_hospital_data.parquet', index=False)
print(f"  ✓ Full merged dataset: data/processed/merged_hospital_data.parquet")
print(f"    ({len(merged):,} records × {len(merged.columns)} columns)")

# Save segmentation summary
seg_cols = ['pn', 'year', 'dea_efficiency', 'hospital_stratification',
            'clinical_risk_score', 'safety_net_category', 'total_risk', 'risk_profile',
            'margin', 'experience_score', 'beds_adultped_wtd', 'all_readm_rate']
if 'medicaid_share' in merged.columns:
    seg_cols.append('medicaid_share')
if 'uccare_burden' in merged.columns:
    seg_cols.append('uccare_burden')

avail_seg_cols = [c for c in seg_cols if c in merged.columns]
seg = merged[avail_seg_cols].copy()
seg.to_parquet('data/processed/safety_net_segmentation.parquet', index=False)
print(f"  ✓ Segmentation: data/processed/safety_net_segmentation.parquet")

# ============================================================================
# STEP 9: Safety Net Insights Summary
# ============================================================================
print("\n" + "=" * 80)
print("🔍 SAFETY NET HOSPITAL INSIGHTS")
print("=" * 80)

latest_year = int(merged['year'].max())
current = merged[merged['year'] == latest_year]

print(f"\n📅 Latest Year: {latest_year}")
print(f"   Hospitals: {current['pn'].nunique():,}")

# Safety Net + Efficiency Cross-tab
print(f"\n🏥 Safety Net Status vs Efficiency:")
for sn_cat in ['HIGH', 'MODERATE', 'LIMITED', 'LOW']:
    subset = current[current['safety_net_category'] == sn_cat]
    if len(subset) > 0:
        avg_eff = subset['dea_efficiency'].mean()
        avg_margin = subset['margin'].mean() if 'margin' in subset.columns else np.nan
        avg_risk = subset['total_risk'].mean()
        n = len(subset)
        print(f"   {sn_cat:>10} burden: {n:>5,} hospitals | "
              f"Avg Efficiency: {avg_eff:.3f} | "
              f"Avg Margin: {avg_margin:.3f} | "
              f"Avg Risk: {avg_risk:.1f}")

# Critical hospitals that are also safety net
sn_critical = current[
    (current['safety_net_category'].isin(['HIGH', 'MODERATE'])) &
    (current['risk_profile'].isin(['CRITICAL', 'HIGH']))
]
print(f"\n⚠️ HIGH-RISK SAFETY NET HOSPITALS: {len(sn_critical):,}")
print(f"   These hospitals serve vulnerable populations AND face closure risk.")

# Efficiency gap
if 'medicaid_share' in current.columns:
    high_med = current[current['medicaid_share'] >= 0.20]
    low_med = current[current['medicaid_share'] < 0.10]
    if len(high_med) > 0 and len(low_med) > 0:
        print(f"\n📊 Medicaid Burden Impact:")
        print(f"   High Medicaid (≥20%): {len(high_med):,} hospitals, "
              f"Avg Efficiency: {high_med['dea_efficiency'].mean():.3f}, "
              f"Avg Margin: {high_med['margin'].mean():.3f}")
        print(f"   Low Medicaid (<10%):  {len(low_med):,} hospitals, "
              f"Avg Efficiency: {low_med['dea_efficiency'].mean():.3f}, "
              f"Avg Margin: {low_med['margin'].mean():.3f}")
        eff_gap = low_med['dea_efficiency'].mean() - high_med['dea_efficiency'].mean()
        print(f"   Efficiency Gap: {eff_gap:.3f} ({eff_gap/high_med['dea_efficiency'].mean()*100:.1f}% disadvantage)")

print("\n" + "=" * 80)
print("✅ ANALYSIS COMPLETE!")
print("=" * 80)
print(f"\n  Total records:     {len(merged):,}")
print(f"  Total columns:     {len(merged.columns)}")
print(f"  Unique hospitals:  {merged['pn'].nunique():,}")
print(f"  Years:             {int(merged['year'].min())}-{int(merged['year'].max())}")
print(f"  Avg efficiency:    {merged['dea_efficiency'].mean():.3f}")
print(f"\n  Output files:")
print(f"    data/processed/merged_hospital_data.parquet")
print(f"    data/processed/safety_net_segmentation.parquet")
