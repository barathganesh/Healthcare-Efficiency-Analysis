"""
STEP 6-10: Condition-Level DEA Efficiency Analysis
Per Shen et al. (2025) - Input-Oriented VRS DEA

Conditions: AMI, HF, PN, COPD, STK, CABG
For each condition × year:
  INPUTS:  Total Cost, Beds
  OUTPUTS: Survival Rate (1 - mortality), Success Rate (1 - readmission), Patient Volume
"""

import pandas as pd
import numpy as np
from scipy.optimize import linprog
import time

# ─── INPUT-ORIENTED VRS DEA (per paper Section 2.8) ───
def run_dea_vrs(inputs, outputs):
    """Input-oriented Variable Returns to Scale DEA.
    Returns efficiency scores (0-1) for each DMU.
    Uses batch optimization for speed."""
    n_dmu, n_inp = inputs.shape
    n_out = outputs.shape[1]
    scores = np.ones(n_dmu)
    
    for i in range(n_dmu):
        n_vars = 1 + n_dmu
        
        # Objective: minimize theta
        c = np.zeros(n_vars)
        c[0] = 1.0
        
        # Input constraints: theta * x_io >= sum(lambda_j * x_jo)
        A_ub = np.zeros((n_inp + n_out, n_vars))
        b_ub = np.zeros(n_inp + n_out)
        
        for k in range(n_inp):
            A_ub[k, 0] = -inputs[i, k]
            A_ub[k, 1:] = inputs[:, k]
        
        # Output constraints: sum(lambda_j * y_jo) >= y_io
        for k in range(n_out):
            A_ub[n_inp + k, 0] = 0
            A_ub[n_inp + k, 1:] = -outputs[:, k]
            b_ub[n_inp + k] = -outputs[i, k]
        
        # VRS: sum(lambda) = 1
        A_eq = np.zeros((1, n_vars))
        A_eq[0, 1:] = 1.0
        b_eq = np.array([1.0])
        
        bounds = [(1e-6, None)] + [(0, None)] * n_dmu
        
        try:
            result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                           bounds=bounds, method='highs',
                           options={'presolve': True, 'time_limit': 1.0})
            if result.success:
                scores[i] = min(result.x[0], 1.0)
            else:
                scores[i] = np.nan
        except:
            scores[i] = np.nan
    
    return scores


def main():
    t0 = time.time()
    
    print("=" * 80)
    print("STEP 6-10: CONDITION-LEVEL DEA EFFICIENCY ANALYSIS")
    print("           (per Shen et al., 2025 methodology)")
    print("=" * 80)
    
    df = pd.read_parquet('data/processed/merged_hospital_data.parquet')
    print(f"\nLoaded: {len(df):,} records  |  {df['pn'].nunique():,} hospitals")
    
    # ─── DEFINE CONDITIONS ───
    conditions = {
        'AMI': {
            'name': 'Heart Attack (AMI)',
            'mort_rate': 'ami_mort_rate',
            'readm_rate': 'ami_readm_rate',
            'npatients': 'ami_mort_npatients',
        },
        'HF': {
            'name': 'Heart Failure (HF)',
            'mort_rate': 'hf_mort_rate',
            'readm_rate': 'hf_readm_rate',
            'npatients': 'hf_mort_npatients',
        },
        'PN': {
            'name': 'Pneumonia (PN)',
            'mort_rate': 'pn_mort_rate',
            'readm_rate': 'pn_readm_rate',
            'npatients': 'pn_mort_npatients',
        },
        'COPD': {
            'name': 'COPD',
            'mort_rate': 'copd_mort_rate',
            'readm_rate': 'copd_readm_rate',
            'npatients': 'copd_mort_npatients',
        },
        'STK': {
            'name': 'Stroke (STK)',
            'mort_rate': 'stk_mort_rate',
            'readm_rate': 'stk_readm_rate',
            'npatients': 'stk_mort_npatients',
        },
        'CABG': {
            'name': 'Heart Surgery (CABG)',
            'mort_rate': 'cabg_mort_rate',
            'readm_rate': 'cabg_readm_rate',
            'npatients': 'cabg_mort_npatients',
        },
    }
    
    print(f"\n🏥 Running Input-Oriented VRS DEA per condition per year...")
    print(f"   INPUTS:  Total Cost, Beds")
    print(f"   OUTPUTS: Survival Rate (1-mortality), Success Rate (1-readmission), Patient Volume")
    print(f"   Min DMUs required: 15 (3 × [2 inputs + 3 outputs])")
    
    all_results = []
    summary_rows = []
    
    for cond_code, cond_info in conditions.items():
        cond_name = cond_info['name']
        mort_col = cond_info['mort_rate']
        readm_col = cond_info['readm_rate']
        npat_col = cond_info['npatients']
        
        print(f"\n{'─' * 60}")
        print(f"  {cond_name}")
        print(f"{'─' * 60}")
        
        for yr in sorted(df['year'].unique()):
            yr_df = df[df['year'] == yr].copy()
            
            # Filter: must have all required data
            mask = (
                yr_df[mort_col].notna() & 
                yr_df[readm_col].notna() &
                yr_df['totcost'].notna() & (yr_df['totcost'] > 0) &
                yr_df['beds_adultped_wtd'].notna() & (yr_df['beds_adultped_wtd'] > 0) &
                yr_df[npat_col].notna() & (yr_df[npat_col] > 0)
            )
            sub = yr_df[mask].copy()
            
            if len(sub) < 15:
                continue
            
            # INPUTS
            inp = sub[['totcost', 'beds_adultped_wtd']].values.astype(float)
            
            # OUTPUTS (convert rates to "good" outcomes)
            survival_rate = (100.0 - sub[mort_col].values).astype(float)
            success_rate = (100.0 - sub[readm_col].values).astype(float)
            patient_vol = sub[npat_col].values.astype(float)
            
            # Ensure all outputs > 0
            valid = (survival_rate > 0) & (success_rate > 0) & (patient_vol > 0)
            if valid.sum() < 15:
                continue
                
            sub = sub[valid].copy()
            inp = inp[valid]
            out = np.column_stack([survival_rate[valid], success_rate[valid], patient_vol[valid]])
            
            # Normalize to [0,1] range for numerical stability
            inp_norm = inp / inp.max(axis=0)
            out_norm = out / out.max(axis=0)
            
            # Run DEA
            t1 = time.time()
            scores = run_dea_vrs(inp_norm, out_norm)
            elapsed = time.time() - t1
            
            valid_scores = scores[~np.isnan(scores)]
            n_frontier = (valid_scores >= 0.999).sum()
            
            print(f"   {int(yr)}: {len(sub):>5,} hospitals  |  "
                  f"Mean: {np.nanmean(scores):.3f}  Median: {np.nanmedian(scores):.3f}  "
                  f"Frontier: {n_frontier:>4}  |  {elapsed:.1f}s")
            
            summary_rows.append({
                'condition': cond_code,
                'condition_name': cond_name,
                'year': int(yr),
                'n_hospitals': len(sub),
                'mean_efficiency': round(np.nanmean(scores), 4),
                'median_efficiency': round(np.nanmedian(scores), 4),
                'min_efficiency': round(np.nanmin(scores), 4),
                'n_frontier': int(n_frontier),
                'pct_frontier': round(n_frontier / len(valid_scores) * 100, 1),
            })
            
            # Store individual results
            pns = sub['pn'].values
            for j in range(len(sub)):
                all_results.append({
                    'pn': pns[j],
                    'year': int(yr),
                    'condition': cond_code,
                    'efficiency': round(scores[j], 6) if not np.isnan(scores[j]) else np.nan,
                })
    
    total_time = time.time() - t0
    print(f"\n✅ DEA complete in {total_time:.0f}s: {len(all_results):,} scores computed")
    
    # Convert to DataFrames
    results_df = pd.DataFrame(all_results)
    summary_df = pd.DataFrame(summary_rows)
    
    # ─── STEP 10: Average efficiency per hospital ───
    print(f"\n{'=' * 60}")
    print(f"STEP 10: AVERAGE EFFICIENCY PER HOSPITAL")
    print(f"{'=' * 60}")
    
    avg_eff = results_df.groupby('pn').agg(
        avg_efficiency=('efficiency', 'mean'),
        n_conditions=('condition', 'nunique'),
        n_observations=('efficiency', 'count'),
    ).reset_index()
    
    print(f"\n   Hospitals with scores:   {len(avg_eff):,}")
    print(f"   Mean overall efficiency: {avg_eff['avg_efficiency'].mean():.4f}")
    print(f"   Median:                  {avg_eff['avg_efficiency'].median():.4f}")
    print(f"   Min:                     {avg_eff['avg_efficiency'].min():.4f}")
    print(f"   Max:                     {avg_eff['avg_efficiency'].max():.4f}")
    
    # ─── MERGE BACK TO MAIN DATASET ───
    print(f"\n   Merging scores back to main dataset...")
    
    # Pivot condition scores wide
    pivot = results_df.pivot_table(index=['pn', 'year'], columns='condition', 
                                    values='efficiency').reset_index()
    new_cols = ['pn', 'year'] + [f'{c}_efficiency' for c in pivot.columns[2:]]
    pivot.columns = new_cols
    
    # Average per hospital-year
    avg_by_pn_year = results_df.groupby(['pn', 'year'])['efficiency'].mean().reset_index()
    avg_by_pn_year.columns = ['pn', 'year', 'avg_condition_efficiency']
    
    # Merge
    df = df.merge(pivot, on=['pn', 'year'], how='left')
    df = df.merge(avg_by_pn_year, on=['pn', 'year'], how='left')
    
    # Save
    df.to_parquet('data/processed/merged_hospital_data.parquet', index=False)
    results_df.to_csv('data/processed/condition_efficiency_scores.csv', index=False)
    summary_df.to_csv('data/processed/dea_summary_by_condition_year.csv', index=False)
    
    print(f"\n{'=' * 80}")
    print(f"✅ ALL SAVED")
    print(f"{'=' * 80}")
    print(f"   Main dataset:      {len(df):,} records × {len(df.columns)} columns")
    print(f"   New columns:       AMI_efficiency, HF_efficiency, PN_efficiency,")
    print(f"                      COPD_efficiency, STK_efficiency, CABG_efficiency,")
    print(f"                      avg_condition_efficiency")
    print(f"   Condition scores:  data/processed/condition_efficiency_scores.csv")
    print(f"   Summary:           data/processed/dea_summary_by_condition_year.csv")
    
    # Final condition summary
    print(f"\n📊 EFFICIENCY SUMMARY BY CONDITION:")
    print(f"   {'Condition':<25s}  {'N Scores':>10}  {'Mean':>8}  {'Median':>8}  {'Years':>8}")
    for cond in conditions:
        c_df = results_df[results_df['condition'] == cond]
        n_yrs = c_df['year'].nunique()
        print(f"   {conditions[cond]['name']:<25s}  {len(c_df):>10,}  "
              f"{c_df['efficiency'].mean():>8.4f}  {c_df['efficiency'].median():>8.4f}  {n_yrs:>8}")
    
    total = time.time() - t0
    print(f"\n   Total runtime: {total:.0f}s ({total/60:.1f} min)")


if __name__ == '__main__':
    main()
