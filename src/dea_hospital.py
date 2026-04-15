"""
HOSPITAL-LEVEL DEA EFFICIENCY ANALYSIS
Input-Oriented VRS DEA — comparing hospitals to hospitals (not by condition)

INPUTS:  Total Cost, Beds
OUTPUTS: Total Discharges, All-Cause Readmission Success (1 - readm_rate), Total Revenue

This gives an overall efficiency score per hospital-year:
  "How well does this hospital convert its cost & beds into
   patient throughput, low readmissions, and revenue?"
"""

import pandas as pd
import numpy as np
from scipy.optimize import linprog
import time


# ─── INPUT-ORIENTED VRS DEA ───
def run_dea_vrs(inputs, outputs):
    """Input-oriented Variable Returns to Scale DEA.
    Returns efficiency scores (0-1) for each DMU."""
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
    print("HOSPITAL-LEVEL DEA EFFICIENCY ANALYSIS")
    print("  Input-Oriented VRS DEA (per Shen et al., 2025)")
    print("=" * 80)

    df = pd.read_parquet('data/processed/merged_hospital_data.parquet')
    print(f"\nLoaded: {len(df):,} records  |  {df['pn'].nunique():,} hospitals")

    # ─── DEFINE INPUTS & OUTPUTS ───
    # Compute a hospital-level avg readmission success rate from condition-level data
    readm_cols = ['ami_readm_rate', 'hf_readm_rate', 'pn_readm_rate',
                  'copd_readm_rate', 'stk_readm_rate', 'cabg_readm_rate']
    existing_readm = [c for c in readm_cols if c in df.columns]
    df['avg_readm_rate'] = df[existing_readm].mean(axis=1)  # mean of available conditions
    # Use all_readm_rate where available, otherwise fall back to condition average
    df['readm_success_rate'] = 1.0 - df['all_readm_rate'].fillna(df['avg_readm_rate'])

    print(f"\n   INPUTS:  Total Cost, Beds")
    print(f"   OUTPUTS: Total Discharges, Readmission Success Rate, Total Revenue")
    print(f"   Readmission: all_readm_rate (2012+) or avg of condition rates (2007-2011)")
    print(f"   Min DMUs required: 15 (3 × [2 inputs + 3 outputs])")

    all_results = []
    summary_rows = []

    print(f"\n{'─' * 70}")
    print(f"  Running DEA per year...")
    print(f"{'─' * 70}")

    for yr in sorted(df['year'].unique()):
        yr_df = df[df['year'] == yr].copy()

        # Filter: must have all required data > 0
        mask = (
            yr_df['totcost'].notna() & (yr_df['totcost'] > 0) &
            yr_df['beds_adultped_wtd'].notna() & (yr_df['beds_adultped_wtd'] > 0) &
            yr_df['ipdischarges_adultped'].notna() & (yr_df['ipdischarges_adultped'] > 0) &
            yr_df['readm_success_rate'].notna() & (yr_df['readm_success_rate'] > 0) &
            yr_df['tottotrev'].notna() & (yr_df['tottotrev'] > 0)
        )
        sub = yr_df[mask].copy()

        if len(sub) < 15:
            print(f"   {int(yr)}: SKIPPED ({len(sub)} hospitals — below minimum)")
            continue

        # INPUTS
        inp = sub[['totcost', 'beds_adultped_wtd']].values.astype(float)

        # OUTPUTS
        out = sub[['ipdischarges_adultped', 'readm_success_rate', 'tottotrev']].values.astype(float)

        # Normalize for numerical stability
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
            'year': int(yr),
            'n_hospitals': len(sub),
            'mean_efficiency': round(np.nanmean(scores), 4),
            'median_efficiency': round(np.nanmedian(scores), 4),
            'min_efficiency': round(np.nanmin(scores), 4),
            'n_frontier': int(n_frontier),
        })

        # Store individual results
        pns = sub['pn'].values
        for j in range(len(sub)):
            all_results.append({
                'pn': pns[j],
                'year': int(yr),
                'hospital_efficiency': round(scores[j], 6) if not np.isnan(scores[j]) else np.nan,
            })

    total_time = time.time() - t0
    print(f"\n✅ DEA complete in {total_time:.0f}s: {len(all_results):,} scores computed")

    # Convert to DataFrames
    results_df = pd.DataFrame(all_results)
    summary_df = pd.DataFrame(summary_rows)

    # ─── HOSPITAL AVERAGE ACROSS YEARS ───
    print(f"\n{'=' * 70}")
    print(f"HOSPITAL AVERAGE EFFICIENCY (across all years)")
    print(f"{'=' * 70}")

    hosp_avg = results_df.groupby('pn').agg(
        avg_hospital_efficiency=('hospital_efficiency', 'mean'),
        n_years=('year', 'nunique'),
    ).reset_index()

    print(f"\n   Hospitals with scores:   {len(hosp_avg):,}")
    print(f"   Mean efficiency:         {hosp_avg['avg_hospital_efficiency'].mean():.4f}")
    print(f"   Median:                  {hosp_avg['avg_hospital_efficiency'].median():.4f}")

    # ─── MERGE BACK TO MAIN DATASET ───
    print(f"\n   Merging hospital_efficiency back to main dataset...")

    # Drop any pre-existing hospital_efficiency columns to avoid _x/_y conflicts
    for col in ['hospital_efficiency', 'hospital_efficiency_x', 'hospital_efficiency_y',
                'readm_success_rate', 'avg_readm_rate']:
        if col in df.columns:
            df = df.drop(columns=[col])

    results_df['pn'] = results_df['pn'].astype(str)
    df = df.merge(results_df[['pn', 'year', 'hospital_efficiency']],
                  on=['pn', 'year'], how='left')

    # Save
    df.to_parquet('data/processed/merged_hospital_data.parquet', index=False)
    results_df.to_csv('data/processed/hospital_efficiency_scores.csv', index=False)
    summary_df.to_csv('data/processed/dea_hospital_summary_by_year.csv', index=False)

    print(f"\n{'=' * 80}")
    print(f"✅ ALL SAVED")
    print(f"{'=' * 80}")
    print(f"   Main dataset:       {len(df):,} records × {len(df.columns)} columns")
    print(f"   New column:         hospital_efficiency")
    print(f"   Scores CSV:         data/processed/hospital_efficiency_scores.csv")
    print(f"   Summary CSV:        data/processed/dea_hospital_summary_by_year.csv")

    # ─── COMPARE condition-level vs hospital-level ───
    both = df[df['avg_condition_efficiency'].notna() & df['hospital_efficiency'].notna()]
    if len(both) > 0:
        corr = both['avg_condition_efficiency'].corr(both['hospital_efficiency'])
        print(f"\n📊 Correlation between condition-level avg and hospital-level efficiency: {corr:.4f}")
        print(f"   (Shows how well they agree — 1.0 = perfect agreement)")

    print(f"\n   Total runtime: {time.time() - t0:.0f}s")


if __name__ == '__main__':
    main()
