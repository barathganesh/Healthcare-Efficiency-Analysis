"""
Step 19 — Healthcare Analytics Visualizations
==============================================
Generates 10 publication-quality charts for the Shen et al. (2025)
hospital efficiency research pipeline.

Value Framework:
  Value = Clinical Quality + Equity Contribution
  Clinical Quality  = risk-adjusted mortality + risk-adjusted readmissions
  Equity Contribution = Medicaid share (serving vulnerable communities)

Outputs saved to: outputs/Visualizations/
"""

import os, warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

# ── Paths ──
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'data', 'processed')
OUT  = os.path.join(BASE, 'outputs', 'Visualizations')
os.makedirs(OUT, exist_ok=True)

# ── Style ──
sns.set_style('whitegrid')
plt.rcParams.update({
    'figure.dpi': 200,
    'savefig.dpi': 200,
    'savefig.bbox': 'tight',
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
})

HERO_COLOR = '#2ecc71'
MIDDLE_COLOR = '#3498db'
STRUGGLER_COLOR = '#e74c3c'
GROUP_COLORS = {'HERO': HERO_COLOR, 'MIDDLE': MIDDLE_COLOR, 'STRUGGLER': STRUGGLER_COLOR}
ACCENT = '#8e44ad'

# ── Load data ──
print('Loading data...')
df      = pd.read_parquet(os.path.join(DATA, 'merged_hospital_data.parquet'))
optim   = pd.read_csv(os.path.join(DATA, 'struggler_optimization_prescriptions.csv'))
detail  = pd.read_csv(os.path.join(DATA, 'struggler_stress_test_detail.csv'))
summary = pd.read_csv(os.path.join(DATA, 'stress_test_summary.csv'))
impact  = pd.read_csv(os.path.join(DATA, 'total_impact_summary.csv'))
hero_vs = pd.read_csv(os.path.join(DATA, 'hero_vs_struggler_comparison.csv'))
ml_feat = pd.read_csv(os.path.join(DATA, 'ml_feature_importance.csv'))
by_state= pd.read_csv(os.path.join(DATA, 'struggler_optimization_by_state.csv'))
eff     = pd.read_csv(os.path.join(DATA, 'hospital_efficiency_scores.csv'))

# Latest observation per hospital
latest = df.sort_values('year').groupby('pn').last().reset_index()

print(f'  {len(latest):,} unique hospitals  |  {len(optim)} Strugglers with prescriptions')


# =====================================================================
# VIZ 1: VALUE FRAMEWORK — Clinical Quality vs Equity Contribution
# =====================================================================
def viz01_value_framework():
    print('  [1/10] Value Framework scatter...')
    # Use each hospital at the year it was classified, so all 232 Strugglers appear
    # For Strugglers: use their Struggler-year observation
    # For others: use their latest observation
    group_priority = {'HERO': 2, 'STRUGGLER': 1, 'MIDDLE': 0}
    df_scored = df.dropna(subset=['avg_mort_rate', 'avg_readm_rate_calc', 'medicaid_share', 'hospital_group']).copy()
    df_scored['_gprio'] = df_scored['hospital_group'].map(group_priority)
    d = df_scored.sort_values(['_gprio', 'year'], ascending=[False, False]).groupby('pn').first().reset_index()

    # Clinical Quality score (inverted: lower mort/readm = higher quality)
    d['clinical_quality'] = 1 - (d['avg_mort_rate'] + d['avg_readm_rate_calc']) / 2
    # Equity Contribution = Medicaid share
    d['equity'] = d['medicaid_share']

    fig, ax = plt.subplots(figsize=(10, 7))

    for grp in ['MIDDLE', 'STRUGGLER', 'HERO']:
        sub = d[d['hospital_group'] == grp]
        ax.scatter(sub['equity'] * 100, sub['clinical_quality'] * 100,
                   c=GROUP_COLORS[grp], label=grp.title(),
                   alpha=0.35 if grp == 'MIDDLE' else 0.85,
                   s=25 if grp == 'MIDDLE' else 70,
                   edgecolors='white', linewidth=0.3,
                   zorder=2 if grp == 'MIDDLE' else 3)

    ax.set_xlabel('Equity Contribution  (Medicaid Share %)', fontsize=12)
    ax.set_ylabel('Clinical Quality Score  (100 = perfect)', fontsize=12)
    ax.set_title('Hospital Value Framework\nValue = Clinical Quality + Equity Contribution', fontsize=15)
    ax.legend(loc='lower left', fontsize=11, frameon=True, facecolor='white')

    # Annotate quadrants
    ax.axhline(d['clinical_quality'].median() * 100, color='grey', ls='--', lw=0.7, alpha=0.5)
    ax.axvline(d['equity'].median() * 100, color='grey', ls='--', lw=0.7, alpha=0.5)
    ax.text(0.98, 0.98, 'High Quality\nHigh Equity →\nHighest Value', transform=ax.transAxes,
            ha='right', va='top', fontsize=9, color='#27ae60', fontstyle='italic')
    ax.text(0.02, 0.02, '← Low Quality\nLow Equity\nLowest Value', transform=ax.transAxes,
            ha='left', va='bottom', fontsize=9, color='#c0392b', fontstyle='italic')

    plt.savefig(os.path.join(OUT, '01_value_framework.png'))
    plt.close()


# =====================================================================
# VIZ 2: US CHOROPLETH — Struggler Hospitals At Risk by State
# =====================================================================
def viz02_closure_risk_map():
    print('  [2/10] US closure-risk choropleth map...')

    # Use detail.csv which has all 232 Struggler hospitals at their classified year
    strugg_per_state = detail.groupby('state').size().reset_index(name='struggler_count')

    # Closure risk hospitals per state (under 10% Medicaid cut, without optimization)
    closure_by_state = detail[detail['status_after_medicaid_cut'] == 'CLOSURE_RISK'].groupby('state').size().reset_index(name='closure_risk')
    merged = strugg_per_state.merge(closure_by_state, on='state', how='left').fillna(0)
    merged['closure_risk'] = merged['closure_risk'].astype(int)

    fig = px.choropleth(
        merged, locations='state', locationmode='USA-states',
        color='struggler_count', scope='usa',
        color_continuous_scale='YlOrRd',
        labels={'struggler_count': 'Struggler<br>Hospitals'},
        title='Struggler Hospitals at Risk Across the US<br><sup>Hospitals that need optimization to survive Medicaid cuts</sup>',
    )
    fig.update_layout(
        geo=dict(bgcolor='rgba(0,0,0,0)', lakecolor='#e8f4fd'),
        margin=dict(l=0, r=0, t=60, b=0),
        font=dict(size=13),
        width=1000, height=550,
    )
    fig.write_image(os.path.join(OUT, '02_closure_risk_map.png'), scale=2)


# =====================================================================
# VIZ 3: STRESS TEST — Hospitals Saved (Before/After Optimization)
# =====================================================================
def viz03_stress_test_before_after():
    print('  [3/10] Stress test before/after bars...')

    scenarios = ['10% Medicaid Cut', '10% Medicaid + 10% Medicare',
                 '25% Medicaid Cut', '30% Medicaid + 10% Medicare']
    short_names = ['10% Medicaid', '10% Med+Care', '25% Medicaid', '30% Med+Care']

    without_closure = []
    with_closure = []
    without_neg = []
    with_neg = []

    for sc in scenarios:
        sec = f'Scenario: {sc}'
        s = summary[summary['section'] == sec]
        without_closure.append(int(s[s['metric'].str.contains('WITHOUT:.*closure')]['value'].values[0]))
        with_closure.append(int(s[s['metric'].str.contains('^WITH:.*closure', regex=True)]['value'].values[0]))
        without_neg.append(int(s[s['metric'].str.contains('WITHOUT:.*negative')]['value'].values[0]))
        with_neg.append(int(s[s['metric'].str.contains('^WITH:.*negative', regex=True)]['value'].values[0]))

    x = np.arange(len(scenarios))
    w = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), sharey=False)

    # Panel A: Closure risk
    bars1 = ax1.bar(x - w/2, without_closure, w, label='Without Optimization',
                     color='#e74c3c', alpha=0.85, edgecolor='white')
    bars2 = ax1.bar(x + w/2, with_closure, w, label='With Optimization',
                     color='#2ecc71', alpha=0.85, edgecolor='white')
    ax1.set_title('Closure Risk  (margin < −5%)', fontsize=13)
    ax1.set_ylabel('Number of Hospitals')
    ax1.set_xticks(x)
    ax1.set_xticklabels(short_names, fontsize=9)
    ax1.legend(fontsize=9)
    for b in bars1:
        ax1.text(b.get_x() + b.get_width()/2, b.get_height() + 1, int(b.get_height()),
                 ha='center', va='bottom', fontsize=9, fontweight='bold', color='#c0392b')
    for b in bars2:
        ax2_val = int(b.get_height())
        ax1.text(b.get_x() + b.get_width()/2, b.get_height() + 1, ax2_val,
                 ha='center', va='bottom', fontsize=9, fontweight='bold', color='#27ae60')

    # Panel B: Negative margin
    bars3 = ax2.bar(x - w/2, without_neg, w, label='Without Optimization',
                     color='#e74c3c', alpha=0.85, edgecolor='white')
    bars4 = ax2.bar(x + w/2, with_neg, w, label='With Optimization',
                     color='#2ecc71', alpha=0.85, edgecolor='white')
    ax2.set_title('Negative Margin  (margin < 0%)', fontsize=13)
    ax2.set_ylabel('Number of Hospitals')
    ax2.set_xticks(x)
    ax2.set_xticklabels(short_names, fontsize=9)
    ax2.legend(fontsize=9)
    for b in bars3:
        ax2.text(b.get_x() + b.get_width()/2, b.get_height() + 1, int(b.get_height()),
                 ha='center', va='bottom', fontsize=9, fontweight='bold', color='#c0392b')
    for b in bars4:
        ax2.text(b.get_x() + b.get_width()/2, b.get_height() + 1, int(b.get_height()),
                 ha='center', va='bottom', fontsize=9, fontweight='bold', color='#27ae60')

    fig.suptitle('Stress Test: Optimization as an Insurance Policy\n232 Struggler Hospitals Under Funding Cut Scenarios',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, '03_stress_test_before_after.png'))
    plt.close()


# =====================================================================
# VIZ 4: LIVES SAVED ACROSS SCENARIOS
# =====================================================================
def viz04_lives_saved():
    print('  [4/10] Lives saved chart...')

    scenarios = ['10% Medicaid Cut', '10% Medicaid + 10% Medicare',
                 '25% Medicaid Cut', '30% Medicaid + 10% Medicare']
    short_names = ['10%\nMedicaid', '10% Medicaid\n+ 10% Medicare',
                   '25%\nMedicaid', '30% Medicaid\n+ 10% Medicare']

    lives = []
    closures_saved = []
    for sc in scenarios:
        sec = f'Scenario: {sc}'
        s = summary[summary['section'] == sec]
        lives.append(int(s[s['metric'].str.contains('lives')]['value'].values[0]))
        closures_saved.append(int(s[s['metric'].str.contains('saved from closure')]['value'].values[0]))

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#f39c12', '#e67e22', '#e74c3c', '#c0392b']
    bars = ax.bar(range(len(scenarios)), lives, color=colors, edgecolor='white', linewidth=1.5)

    for i, (bar, l, c) in enumerate(zip(bars, lives, closures_saved)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 15,
                f'{l:,}\nlives', ha='center', va='bottom', fontsize=11, fontweight='bold')
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 0.5,
                f'{c} hospitals\nsaved from\nclosure', ha='center', va='center',
                fontsize=9, color='white', fontweight='bold')

    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels(short_names, fontsize=10)
    ax.set_ylabel('Excess Lives Saved (deaths prevented)', fontsize=12)
    ax.set_title('Lives Saved by Optimization Under Funding Cut Scenarios\n17 excess deaths prevented per hospital closure avoided',
                 fontsize=13)
    ax.set_ylim(0, max(lives) * 1.25)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.savefig(os.path.join(OUT, '04_lives_saved.png'))
    plt.close()


# =====================================================================
# VIZ 5: COST SAVINGS BREAKDOWN BY FIX TYPE
# =====================================================================
def viz05_cost_savings_breakdown():
    print('  [5/10] Cost savings breakdown...')

    imp = impact[impact['Category'] == 'BY FIX TYPE'].copy()

    fixes = {
        'Fix 1: Admin Overhead\nReduction': float(imp[imp['Metric'].str.contains('Fix 1.*Overhead|Fix 1.*Admin')]['Value'].values[0]),
        'Fix 2: Nursing\nInvestment (Cost)': -float(imp[imp['Metric'].str.contains('Fix 2.*Cost')]['Value'].values[0]),
        'Fix 3: Occupancy\nRevenue Gain': float(imp[imp['Metric'].str.contains('Fix 3.*Revenue')]['Value'].values[0]),
        'Fix 4: Contract\nLabor Savings': float(imp[imp['Metric'].str.contains('Fix 4.*Contract Labor Savings')]['Value'].values[0]),
        'Fix 5: Readmission\nSavings': float(imp[imp['Metric'].str.contains('Fix 5.*Readmission Savings')]['Value'].values[0]),
    }

    labels = list(fixes.keys())
    values = [v / 1e6 for v in fixes.values()]
    colors_list = ['#27ae60', '#e74c3c', '#2980b9', '#8e44ad', '#f39c12']

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.barh(labels, values, color=colors_list, edgecolor='white', height=0.6)
    for bar, v in zip(bars, values):
        offset = 10 if v >= 0 else -10
        ha = 'left' if v >= 0 else 'right'
        ax.text(v + offset, bar.get_y() + bar.get_height()/2,
                f'${abs(v):,.0f}M', va='center', ha=ha, fontsize=11, fontweight='bold')

    ax.axvline(0, color='black', lw=0.8)
    ax.set_xlabel('Annual Impact ($ Millions)', fontsize=12)
    ax.set_title('$2.44 Billion in Annual Optimization Savings\nBreakdown by Fix Type Across 232 Struggler Hospitals',
                 fontsize=13)
    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Net total annotation
    net = sum(fixes.values()) / 1e9
    ax.text(0.98, 0.05, f'Net Total: ${net:.2f}B / year',
            transform=ax.transAxes, ha='right', va='bottom',
            fontsize=13, fontweight='bold', color='#27ae60',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#eafaf1', edgecolor='#27ae60'))

    plt.savefig(os.path.join(OUT, '05_cost_savings_breakdown.png'))
    plt.close()


# =====================================================================
# VIZ 6: HERO vs STRUGGLER — Radar Chart
# =====================================================================
def viz06_hero_vs_struggler_radar():
    print('  [6/10] Hero vs Struggler radar...')

    # Pick key comparable metrics
    metrics_map = {
        'DEA Efficiency Score': 'Efficiency',
        'Avg Mortality Rate': 'Low Mortality',
        'Readmission Rate': 'Low Readmission',
        'Occupancy Rate': 'Occupancy',
        'Operating Margin': 'Margin',
        'HCAHPS Overall Score': 'Patient\nSatisfaction',
    }

    h = hero_vs.copy()
    hero_vals = []
    strugg_vals = []
    labels_r = []

    for metric, label in metrics_map.items():
        row = h[h['Characteristic'] == metric]
        if len(row) == 0:
            continue
        hv = row['Heroes'].values[0]
        sv = row['Strugglers'].values[0]
        # Parse: remove %, $, commas
        hv = float(str(hv).replace('%', '').replace('$', '').replace(',', '').strip())
        sv = float(str(sv).replace('%', '').replace('$', '').replace(',', '').strip())

        # For mortality/readmission, invert (lower is better)
        if 'Mort' in metric or 'Readm' in metric:
            hv = 100 - hv
            sv = 100 - sv

        hero_vals.append(hv)
        strugg_vals.append(sv)
        labels_r.append(label)

    # Normalize to 0-100 scale
    max_vals = [max(h_v, s) * 1.1 for h_v, s in zip(hero_vals, strugg_vals)]
    hero_norm = [h_v / m * 100 for h_v, m in zip(hero_vals, max_vals)]
    strugg_norm = [s / m * 100 for s, m in zip(strugg_vals, max_vals)]

    N = len(labels_r)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    hero_norm += hero_norm[:1]
    strugg_norm += strugg_norm[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.fill(angles, hero_norm, alpha=0.2, color=HERO_COLOR)
    ax.plot(angles, hero_norm, color=HERO_COLOR, linewidth=2.5, label='Heroes (85)')
    ax.fill(angles, strugg_norm, alpha=0.2, color=STRUGGLER_COLOR)
    ax.plot(angles, strugg_norm, color=STRUGGLER_COLOR, linewidth=2.5, label='Strugglers (232)')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels_r, fontsize=11)
    ax.set_yticklabels([])
    ax.set_title('Hero vs Struggler Hospital Profile\nNormalized Performance Comparison',
                 fontsize=14, fontweight='bold', pad=25)
    ax.legend(loc='lower right', bbox_to_anchor=(1.15, -0.05), fontsize=11)

    plt.savefig(os.path.join(OUT, '06_hero_vs_struggler_radar.png'))
    plt.close()


# =====================================================================
# VIZ 7: MARGIN BEFORE/AFTER OPTIMIZATION — Distribution
# =====================================================================
def viz07_margin_before_after():
    print('  [7/10] Margin before/after distribution...')

    current = optim['current_margin'] * 100
    projected = optim['projected_margin'] * 100

    fig, ax = plt.subplots(figsize=(11, 6))

    # KDE plots
    sns.kdeplot(current, ax=ax, color=STRUGGLER_COLOR, fill=True, alpha=0.35,
                linewidth=2.5, label=f'Before Optimization (mean {current.mean():.1f}%)')
    sns.kdeplot(projected, ax=ax, color=HERO_COLOR, fill=True, alpha=0.35,
                linewidth=2.5, label=f'After Optimization (mean {projected.mean():.1f}%)')

    # Vertical lines at means
    ax.axvline(current.mean(), color=STRUGGLER_COLOR, ls='--', lw=1.5)
    ax.axvline(projected.mean(), color=HERO_COLOR, ls='--', lw=1.5)

    # Zero line
    ax.axvline(0, color='black', ls='-', lw=1, alpha=0.5)
    ax.axvspan(-100, 0, alpha=0.05, color='red')

    # Arrow showing improvement
    ymax = ax.get_ylim()[1]
    ax.annotate('', xy=(projected.mean(), ymax * 0.6),
                xytext=(current.mean(), ymax * 0.6),
                arrowprops=dict(arrowstyle='->', color=ACCENT, lw=2.5))
    ax.text((current.mean() + projected.mean()) / 2, ymax * 0.65,
            f'+{projected.mean() - current.mean():.1f}pp',
            ha='center', fontsize=13, fontweight='bold', color=ACCENT)

    ax.set_xlabel('Operating Margin (%)', fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.set_title('Margin Transformation: 232 Struggler Hospitals\nBefore vs After Optimization Prescriptions',
                 fontsize=14)
    ax.legend(fontsize=11, loc='upper right')
    ax.set_xlim(-30, 80)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.savefig(os.path.join(OUT, '07_margin_before_after.png'))
    plt.close()


# =====================================================================
# VIZ 8: TOP ML FEATURES — What Separates Heroes from Strugglers
# =====================================================================
def viz08_ml_feature_importance():
    print('  [8/10] ML feature importance...')

    top = ml_feat.head(15).copy()
    top = top.sort_values('Avg_Rank', ascending=False)

    fig, ax = plt.subplots(figsize=(10, 7))

    # Use average of RF and GB importance
    top['avg_imp'] = (top['RF_Importance'] + top['GB_Importance']) / 2

    colors_feat = [HERO_COLOR if '↑' in str(d) else STRUGGLER_COLOR
                   for d in top['Direction']]

    bars = ax.barh(top['Feature'], top['avg_imp'], color=colors_feat,
                   edgecolor='white', height=0.65)

    ax.set_xlabel('Feature Importance (avg of Random Forest + Gradient Boosting)', fontsize=11)
    ax.set_title('What Makes a Hospital a Hero vs Struggler?\nTop 15 ML Features (99.4% classification accuracy)',
                 fontsize=13)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Legend
    hero_patch = mpatches.Patch(color=HERO_COLOR, label='Higher → Hero')
    strugg_patch = mpatches.Patch(color=STRUGGLER_COLOR, label='Lower → Hero')
    ax.legend(handles=[hero_patch, strugg_patch], loc='lower right', fontsize=10)

    plt.savefig(os.path.join(OUT, '08_ml_feature_importance.png'))
    plt.close()


# =====================================================================
# VIZ 9: STATE-LEVEL IMPACT MAP — Lives Saved by State
# =====================================================================
def viz09_state_impact_map():
    print('  [9/10] State-level impact choropleth...')

    total_lives = int(by_state['total_lives_saved'].sum())

    fig = px.choropleth(
        by_state, locations='state', locationmode='USA-states',
        color='total_lives_saved', scope='usa',
        color_continuous_scale='Greens',
        hover_data={'state': True, 'n_hospitals': True,
                    'total_net_savings': ':$,.0f', 'total_lives_saved': ':,.0f'},
        labels={'total_lives_saved': 'Lives<br>Saved', 'n_hospitals': 'Hospitals',
                'total_net_savings': 'Net Savings ($)'},
        title=f'Lives Saved by State Through Hospital Optimization<br>'
              f'<sup>232 Struggler hospitals across {len(by_state)} states  |  '
              f'Total: {total_lives:,} lives/year</sup>',
    )
    fig.update_layout(
        geo=dict(bgcolor='rgba(0,0,0,0)', lakecolor='#e8f4fd'),
        margin=dict(l=0, r=0, t=70, b=0),
        font=dict(size=13),
        width=1000, height=550,
    )
    fig.write_image(os.path.join(OUT, '09_state_impact_map.png'), scale=2)


# =====================================================================
# VIZ 10: CLINICAL QUALITY GAP — Mortality & Readmission by Group
# =====================================================================
def viz10_clinical_quality_gap():
    print('  [10/10] Clinical quality gap...')

    conditions = ['AMI', 'HF', 'PN']
    full_names = ['Heart Attack\n(AMI)', 'Heart Failure\n(HF)', 'Pneumonia\n(PN)']

    h = hero_vs.copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # ── Panel A: Mortality ──
    hero_mort = []
    strugg_mort = []
    for cond in conditions:
        row = h[h['Characteristic'] == f'{cond} Mortality Rate']
        hv = float(row['Heroes'].values[0].replace('%', ''))
        sv = float(row['Strugglers'].values[0].replace('%', ''))
        hero_mort.append(hv)
        strugg_mort.append(sv)

    x = np.arange(len(conditions))
    w = 0.35
    ax1.bar(x - w/2, hero_mort, w, label='Heroes', color=HERO_COLOR, edgecolor='white')
    ax1.bar(x + w/2, strugg_mort, w, label='Strugglers', color=STRUGGLER_COLOR, edgecolor='white')

    for i in range(len(conditions)):
        gap = strugg_mort[i] - hero_mort[i]
        ax1.annotate(f'−{gap:.1f}pp', xy=(x[i], max(hero_mort[i], strugg_mort[i]) + 0.3),
                     ha='center', fontsize=10, fontweight='bold', color=ACCENT)

    ax1.set_xticks(x)
    ax1.set_xticklabels(full_names, fontsize=10)
    ax1.set_ylabel('Risk-Adjusted Mortality Rate (%)', fontsize=11)
    ax1.set_title('Mortality Gap', fontsize=13)
    ax1.legend(fontsize=10)
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # ── Panel B: Readmission ──
    hero_readm = []
    strugg_readm = []
    for cond in conditions:
        row = h[h['Characteristic'] == f'{cond} Readmission Rate']
        hv = float(row['Heroes'].values[0].replace('%', ''))
        sv = float(row['Strugglers'].values[0].replace('%', ''))
        hero_readm.append(hv)
        strugg_readm.append(sv)

    ax2.bar(x - w/2, hero_readm, w, label='Heroes', color=HERO_COLOR, edgecolor='white')
    ax2.bar(x + w/2, strugg_readm, w, label='Strugglers', color=STRUGGLER_COLOR, edgecolor='white')

    for i in range(len(conditions)):
        gap = strugg_readm[i] - hero_readm[i]
        ax2.annotate(f'−{gap:.1f}pp', xy=(x[i], max(hero_readm[i], strugg_readm[i]) + 0.3),
                     ha='center', fontsize=10, fontweight='bold', color=ACCENT)

    ax2.set_xticks(x)
    ax2.set_xticklabels(full_names, fontsize=10)
    ax2.set_ylabel('Risk-Adjusted Readmission Rate (%)', fontsize=11)
    ax2.set_title('Readmission Gap', fontsize=13)
    ax2.legend(fontsize=10)
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    fig.suptitle('Clinical Quality: Heroes vs Strugglers\nRisk-Adjusted Outcomes by Condition  (lower = better)',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, '10_clinical_quality_gap.png'))
    plt.close()


# =====================================================================
# RUN ALL
# =====================================================================
if __name__ == '__main__':
    print('\n' + '='*60)
    print('STEP 19 — Generating 10 Visualizations')
    print('='*60)

    viz01_value_framework()
    viz02_closure_risk_map()
    viz03_stress_test_before_after()
    viz04_lives_saved()
    viz05_cost_savings_breakdown()
    viz06_hero_vs_struggler_radar()
    viz07_margin_before_after()
    viz08_ml_feature_importance()
    viz09_state_impact_map()
    viz10_clinical_quality_gap()

    print('\n' + '='*60)
    print(f'✅ All 10 visualizations saved to: outputs/Visualizations/')
    print('='*60)
    for f in sorted(os.listdir(OUT)):
        if f.endswith('.png'):
            size = os.path.getsize(os.path.join(OUT, f))
            print(f'  {f}  ({size/1024:.0f} KB)')
