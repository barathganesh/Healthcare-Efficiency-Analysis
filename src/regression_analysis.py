"""
SECOND-STAGE REGRESSION ANALYSIS ON DEA EFFICIENCY SCORES
==========================================================
Three models compared:
  1. OLS regression    (primary — R² = 0.665 with 20 variables)
  2. Tobit regression  (censored at 100 — accounts for frontier pile-up)
  3. Logistic regression (binary: top-quartile efficient or not — robustness)

Variable selection: systematic 6-step process
  1. Inventoried all 635 columns → 608 numeric candidates
  2. Filtered to 191 variables with ≥70% non-missing coverage
  3. Removed duplicate _min/_max/_wtd triplicates → 133 unique variables
  4. Correlation analysis → identified 65+ pairs with |r|>0.90
  5. Selected 1 representative per cluster + theory-motivated additions
  6. Progressive model comparison (A→F) to find optimal 20-variable set

Dependent variable: hospital_efficiency × 100 (OLS/Tobit), binary (Logistic)
Independent variables: 20 hospital characteristics + year fixed effects
Observation unit: hospital-year (no aggregation)
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy.optimize import minimize
from scipy.stats import norm
import warnings
import time

warnings.filterwarnings('ignore')


def prepare_data():
    """Load data and prepare regression variables."""
    print("=" * 80)
    print("SECOND-STAGE REGRESSION: What Drives Hospital Efficiency?")
    print("  20 systematically selected variables + year fixed effects")
    print("=" * 80)

    df = pd.read_parquet('data/processed/merged_hospital_data.parquet')
    eff_df = df[df['hospital_efficiency'].notna()].copy()
    print(f"\nObservations with DEA scores: {len(eff_df):,}")

    # ─── DEPENDENT VARIABLES ───
    eff_df['eff_100'] = eff_df['hospital_efficiency'] * 100

    # ─── INDEPENDENT VARIABLES (20 total) ───

    # Hospital Size (2)
    eff_df['beds'] = eff_df['beds_adultped_wtd']
    eff_df['discharges_k'] = eff_df['ipdischarges_adultped'] / 1000

    # Financial (6)
    eff_df['cost_m'] = eff_df['totcost'] / 1e6
    eff_df['revenue_m'] = eff_df['tottotrev'] / 1e6
    eff_df['margin_pct'] = eff_df['margin'] * 100
    eff_df['ccr'] = eff_df['ccr_wtd']
    eff_df['wage_cost_m'] = eff_df['wage_cost_core'] / 1e6
    eff_df['cash_reserves_m'] = eff_df['cash_general_wtd'] / 1e6

    # Balance Sheet (2)
    eff_df['total_assets_m'] = eff_df['tot_asset_general_wtd'] / 1e6
    eff_df['total_liab_m'] = eff_df['tot_liab_general_wtd'] / 1e6

    # Staffing (1)
    eff_df['fte_employees'] = eff_df['fte_employee_payroll_wtd']

    # Demographics (3)
    eff_df['medicaid_pct'] = eff_df['medicaid_share'] * 100
    eff_df['is_teaching'] = (eff_df['teaching_ind'] == 'Y').astype(int)
    eff_df['is_rural'] = (eff_df['rural_ind'] == 2.0).astype(int)

    # Patient Experience — HCAHPS (3)
    eff_df['overall_hcahps'] = eff_df['overall_score']
    eff_df['clean_score_v'] = eff_df['clean_score']
    eff_df['recommend_v'] = eff_df['recommend_score']

    # Clinical Outcomes (3)
    eff_df['hf_readm'] = eff_df['hf_readm_rate']
    eff_df['pn_mort'] = eff_df['pn_mort_rate']
    eff_df['cmi'] = eff_df['tacmiv']

    # Year dummies (reference = 2008, first year with data)
    yr_dum = pd.get_dummies(eff_df['year'].astype(int), prefix='yr', drop_first=True, dtype=int)
    eff_df = pd.concat([eff_df, yr_dum], axis=1)

    # Variable sets
    model_vars = [
        'beds', 'discharges_k', 'cost_m', 'revenue_m', 'margin_pct',
        'medicaid_pct', 'is_teaching', 'is_rural', 'ccr', 'wage_cost_m',
        'cash_reserves_m', 'fte_employees', 'total_assets_m', 'total_liab_m',
        'overall_hcahps', 'clean_score_v', 'recommend_v',
        'hf_readm', 'pn_mort', 'cmi'
    ]
    yr_cols = [c for c in eff_df.columns if c.startswith('yr_')]

    # Drop year dummies with near-zero observations after listwise deletion
    all_x = model_vars + yr_cols
    sub = eff_df[['eff_100'] + all_x].dropna()
    for c in yr_cols[:]:
        if sub[c].sum() < 10:
            print(f"  Dropping {c} (too few obs after listwise deletion)")
            yr_cols.remove(c)

    print(f"  Variables: {len(model_vars)} predictors + {len(yr_cols)} year dummies")
    print(f"  Usable N after listwise deletion: {len(sub):,}")

    return eff_df, model_vars, yr_cols


def run_ols(df, model_vars, yr_cols):
    """Run OLS regression with robust (HC1) standard errors."""
    all_x = model_vars + yr_cols
    sub = df[['eff_100'] + all_x].dropna()
    y = sub['eff_100']
    X = sm.add_constant(sub[all_x])
    model = sm.OLS(y, X).fit(cov_type='HC1')
    return model, len(sub)


def run_tobit(df, model_vars, yr_cols, upper_limit=100):
    """Run Tobit regression (right-censored at upper_limit)."""
    all_x = model_vars + yr_cols
    sub = df[['eff_100'] + all_x].dropna()
    y = sub['eff_100'].values
    X = sm.add_constant(sub[all_x]).values

    # Get OLS starting values
    ols_init = sm.OLS(y, X).fit()
    init_params = np.append(ols_init.params, np.std(ols_init.resid))

    def tobit_ll(params):
        beta = params[:-1]
        sigma = max(params[-1], 1e-6)
        xb = X @ beta
        ll = 0
        uncens = y < upper_limit
        if uncens.any():
            ll += np.sum(-0.5 * np.log(2 * np.pi) - np.log(sigma)
                         - 0.5 * ((y[uncens] - xb[uncens]) / sigma) ** 2)
        cens = ~uncens
        if cens.any():
            ll += np.sum(np.log(np.clip(
                1 - norm.cdf((upper_limit - xb[cens]) / sigma), 1e-300, None)))
        return -ll

    result = minimize(tobit_ll, init_params, method='L-BFGS-B',
                      bounds=[(None, None)] * len(init_params[:-1]) + [(0.01, None)],
                      options={'maxiter': 5000})

    tobit_coefs = result.x[:-1]
    tobit_sigma = result.x[-1]
    var_names = ['const'] + model_vars + yr_cols
    return tobit_coefs, tobit_sigma, result.success, len(sub), var_names


def run_logistic(df, model_vars, yr_cols):
    """Run Logistic regression (top-quartile efficient = 1)."""
    all_x = model_vars + yr_cols
    sub = df[['eff_100', 'hospital_efficiency'] + all_x].dropna()
    threshold = sub['hospital_efficiency'].quantile(0.75)
    sub['is_efficient'] = (sub['hospital_efficiency'] >= threshold).astype(int)

    y = sub['is_efficient']
    X = sm.add_constant(sub[all_x])

    try:
        model = sm.Logit(y, X).fit(method='bfgs', maxiter=1000, disp=0)
    except Exception:
        # Regularized fallback for collinearity
        model = sm.Logit(y, X).fit_regularized(alpha=0.01, disp=0)

    return model, len(sub), threshold


def main():
    t0 = time.time()
    eff_df, model_vars, yr_cols = prepare_data()

    # ─── OLS ───
    print(f"\n{'─' * 80}")
    print("MODEL 1: OLS REGRESSION (Primary)")
    print(f"{'─' * 80}")
    ols_model, n_ols = run_ols(eff_df, model_vars, yr_cols)
    print(f"  R²:          {ols_model.rsquared:.4f}")
    print(f"  Adj R²:      {ols_model.rsquared_adj:.4f}")
    print(f"  AIC:         {ols_model.aic:,.0f}")
    print(f"  N:           {n_ols:,}")
    print(f"\n  {'Variable':<22} {'Coef':>10} {'Std Err':>10} {'p-value':>10} {'Sig':>5}")
    print(f"  {'─' * 60}")
    for v in ['const'] + model_vars:
        c = ols_model.params[v]
        se = ols_model.bse[v]
        p = ols_model.pvalues[v]
        sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
        print(f"  {v:<22} {c:>10.4f} {se:>10.4f} {p:>10.4f} {sig:>5}")

    # ─── Tobit ───
    print(f"\n{'─' * 80}")
    print("MODEL 2: TOBIT REGRESSION (Censored at 100)")
    print(f"{'─' * 80}")
    tobit_coefs, tobit_sigma, tobit_converged, n_tobit, tobit_var_names = \
        run_tobit(eff_df, model_vars, yr_cols)
    print(f"  Converged:   {tobit_converged}")
    print(f"  Sigma:       {tobit_sigma:.3f}")
    print(f"  N:           {n_tobit:,}")

    # ─── Logistic ───
    print(f"\n{'─' * 80}")
    print("MODEL 3: LOGISTIC REGRESSION (Top-quartile)")
    print(f"{'─' * 80}")
    logit_model, n_logit, logit_threshold = run_logistic(eff_df, model_vars, yr_cols)
    pseudo_r2 = logit_model.prsquared if hasattr(logit_model, 'prsquared') else 'N/A'
    print(f"  Pseudo-R²:   {pseudo_r2}")
    print(f"  Threshold:   {logit_threshold:.4f}")
    print(f"  N:           {n_logit:,}")

    # ─── Comparison Table ───
    print(f"\n{'=' * 80}")
    print("THREE-MODEL COEFFICIENT COMPARISON")
    print(f"{'=' * 80}")
    print(f"\n  {'Variable':<22} {'OLS':>12} {'Tobit':>12} {'Logistic':>12} {'Agree':>6}")
    print(f"  {'─' * 70}")

    agree_count = 0
    for i, v in enumerate(model_vars):
        idx = i + 1  # +1 for constant
        ols_c = ols_model.params[v]
        ols_p = ols_model.pvalues[v]
        tob_c = tobit_coefs[idx]
        log_c = logit_model.params[v]

        sig = lambda p: '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
        ols_dir = '+' if ols_c > 0 else '-'
        tob_dir = '+' if tob_c > 0 else '-'
        log_dir = '+' if log_c > 0 else '-'
        agree = 'YES' if (ols_dir == tob_dir == log_dir) else 'NO'
        if agree == 'YES':
            agree_count += 1

        print(f"  {v:<22} {ols_c:>+10.4f}{sig(ols_p):<2} {tob_c:>+10.4f}  {log_c:>+10.4f}  {agree:>5}")

    print(f"\n  Direction agreement: {agree_count}/{len(model_vars)} ({agree_count/len(model_vars)*100:.0f}%)")

    # ─── Save outputs ───
    # Coefficient CSV
    rows = []
    for i, v in enumerate(['const'] + model_vars):
        idx = i
        ols_c = ols_model.params[v]
        ols_p = ols_model.pvalues[v]
        tob_c = tobit_coefs[idx]
        log_c = logit_model.params[v]
        log_p = logit_model.pvalues[v] if hasattr(logit_model, 'pvalues') and v in logit_model.pvalues else np.nan
        rows.append({
            'Variable': v,
            'OLS_coef': round(ols_c, 6),
            'OLS_pvalue': round(ols_p, 6),
            'Tobit_coef': round(tob_c, 6),
            'Logit_coef': round(log_c, 6),
            'Logit_pvalue': round(log_p, 6) if not np.isnan(log_p) else ''
        })
    # Add year dummies
    for i, v in enumerate(yr_cols):
        idx = len(model_vars) + 1 + i
        tob_c = tobit_coefs[idx] if idx < len(tobit_coefs) else np.nan
        ols_c = ols_model.params.get(v, np.nan)
        ols_p = ols_model.pvalues.get(v, np.nan)
        log_c = logit_model.params.get(v, np.nan)
        log_p = logit_model.pvalues[v] if hasattr(logit_model, 'pvalues') and v in logit_model.pvalues else np.nan
        rows.append({
            'Variable': v,
            'OLS_coef': round(ols_c, 6) if not np.isnan(ols_c) else '',
            'OLS_pvalue': round(ols_p, 6) if not np.isnan(ols_p) else '',
            'Tobit_coef': round(tob_c, 6) if not np.isnan(tob_c) else '',
            'Logit_coef': round(log_c, 6) if not np.isnan(log_c) else '',
            'Logit_pvalue': round(log_p, 6) if not np.isnan(log_p) else ''
        })

    pd.DataFrame(rows).to_csv('data/processed/regression_coefficients.csv', index=False)

    # Full report
    with open('outputs/reports/regression_results.txt', 'w') as f:
        f.write("SECOND-STAGE REGRESSION ANALYSIS — NON-SAFETY-NET HOSPITALS\n")
        f.write("Updated Model: 20 Systematically Selected Variables + Year FE\n")
        f.write("=" * 80 + "\n\n")
        f.write("MODEL 1: OLS (Primary)\n")
        f.write(ols_model.summary().as_text())
        f.write(f"\n\nMODEL 2: TOBIT (Censored at 100)\n")
        f.write(f"Converged: {tobit_converged}, Sigma: {tobit_sigma:.3f}\n")
        for i, v in enumerate(tobit_var_names):
            f.write(f"  {v:<25} {tobit_coefs[i]:>+10.4f}\n")
        f.write(f"\n\nMODEL 3: LOGISTIC (Top-quartile)\n")
        if hasattr(logit_model, 'summary'):
            f.write(logit_model.summary().as_text())

    print(f"\n{'=' * 80}")
    print("✅ SAVED")
    print(f"  Coefficients:  data/processed/regression_coefficients.csv")
    print(f"  Full report:   outputs/reports/regression_results.txt")
    print(f"  Runtime:       {time.time() - t0:.1f}s")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    main()
