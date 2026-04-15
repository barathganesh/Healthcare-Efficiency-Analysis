"""
Configuration file for Healthcare Analytics Project
Centralized settings for paths, parameters, and constants
"""
import os
from pathlib import Path

# Project Root
PROJECT_ROOT = Path(__file__).parent.parent

# Data Paths
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_PATH = PROJECT_ROOT / "data" / "processed"
OUTPUT_FIGURES_PATH = PROJECT_ROOT / "outputs" / "figures"
OUTPUT_REPORTS_PATH = PROJECT_ROOT / "outputs" / "reports"

# Raw data files
HCAHPS_RAW = RAW_DATA_PATH / "hcahps.dta"
HCRIS_RAW = RAW_DATA_PATH / "hcris.dta"
MORTREADM_RAW = RAW_DATA_PATH / "mortreadm.dta"
POC_RAW = RAW_DATA_PATH / "poc.dta"

# Processed data files
HCAHPS_PROCESSED = PROCESSED_DATA_PATH / "hcahps_clean.parquet"
HCRIS_PROCESSED = PROCESSED_DATA_PATH / "hcris_clean.parquet"
MORTREADM_PROCESSED = PROCESSED_DATA_PATH / "mortreadm_clean.parquet"
POC_PROCESSED = PROCESSED_DATA_PATH / "poc_clean.parquet"
MERGED_DATA = PROCESSED_DATA_PATH / "merged_hospital_data.parquet"

# Analysis Parameters
HCAHPS_QUARTILE_SEGMENTS = 4  # Segment hospitals by HCAHPS quartiles
MIN_HOSPITAL_OBSERVATIONS = 3  # Minimum years of data per hospital
OUTLIER_THRESHOLD = 3.0  # Standard deviations for outlier detection

# Statistical Test Parameters
SIGNIFICANCE_LEVEL = 0.05
CORRELATION_MIN_OBSERVATIONS = 30

# Variables for analysis
HCAHPS_DIMENSIONS = [
    'clean_score',
    'commdoc_score',
    'commnurse_score',
    'explain_score',
    'help_score',
    'pain_score',
    'quiet_score',
    'recommend_score',
    'overall_score'
]

HCRIS_FINANCIAL_VARS = [
    'beds_adultped_wtd',
    'icu_beds_wtd',
    'iptotrev',  # total patient revenue
    'opexp',      # operating expense
    'margin'      # profit margin
]

CLINICAL_OUTCOME_VARS = [
    'mortality_rate',
    'readmission_rate'
]

# Visualization Settings
PLOT_STYLE = "seaborn-v0_8-darkgrid"
FIGURE_DPI = 300
FIGURE_SIZE_SMALL = (10, 6)
FIGURE_SIZE_MEDIUM = (14, 8)
FIGURE_SIZE_LARGE = (16, 10)
COLOR_PALETTE = "husl"

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
