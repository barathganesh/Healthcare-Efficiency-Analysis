"""
Data Cleaning Module
Handles data validation, missing value treatment, and outlier detection
"""
import logging
import pandas as pd
import numpy as np
from typing import Tuple, Dict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import (
    LOG_FORMAT, OUTLIER_THRESHOLD, MIN_HOSPITAL_OBSERVATIONS,
    HCAHPS_DIMENSIONS, CORRELATION_MIN_OBSERVATIONS
)

logging.basicConfig(format=LOG_FORMAT)
logger = logging.getLogger(__name__)


class DataCleaner:
    """Data cleaning and validation operations"""
    
    @staticmethod
    def clean_hcahps(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean HCAHPS patient satisfaction data
        
        Args:
            df: Raw HCAHPS DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        df = df.copy()
        logger.info("Cleaning HCAHPS data...")
        
        # Standardize provider number format
        df['pn'] = df['pn'].astype(str).str.strip()
        
        # Remove rows with missing provider number or year
        initial_rows = len(df)
        df = df.dropna(subset=['pn', 'year'])
        logger.info(f"Removed {initial_rows - len(df)} rows with missing pn or year")
        
        # Ensure year is integer
        df['year'] = df['year'].astype(int)
        
        # Impute missing HCAHPS scores with median by year
        for col in HCAHPS_DIMENSIONS:
            if col in df.columns:
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
        
        # Remove survey response rate outliers (should be 0-100)
        if 'rrate' in df.columns:
            df = df.loc[(df['rrate'] >= 0) & (df['rrate'] <= 100)]  # type: ignore
        
        # Create composite patient experience score
        df['experience_score'] = df[HCAHPS_DIMENSIONS].mean(axis=1)
        
        logger.info(f"HCAHPS cleaned: {df.shape[0]} records")
        return df
    
    @staticmethod
    def clean_hcris(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean HCRIS financial data
        
        Args:
            df: Raw HCRIS DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        df = df.copy()
        logger.info("Cleaning HCRIS data...")
        
        # Standardize provider number
        df['pn'] = df['pn'].astype(str).str.strip()
        
        # Remove rows with missing provider or year
        initial_rows = len(df)
        df = df.dropna(subset=['pn', 'year'])
        logger.info(f"Removed {initial_rows - len(df)} rows with missing pn or year")
        
        # Ensure year is integer
        df['year'] = df['year'].astype(int)
        
        # Select relevant financial metrics
        bed_cols = ['beds_adultped_wtd', 'icu_beds_wtd', 'beds_total_wtd']
        financial_cols = [col for col in df.columns if '_wtd' in col and col.startswith(('total', 'revenue', 'expense'))]
        
        # Forward fill missing values for bed capacity
        df = df.sort_values(['pn', 'year'])
        for col in bed_cols:
            if col in df.columns:
                df[col] = df.groupby('pn')[col].ffill().bfill()
        
        # Calculate financial metrics
        if 'total_revenue_wtd' in df.columns and 'total_expense_wtd' in df.columns:
            df['operating_margin_pct'] = (
                (df['total_revenue_wtd'] - df['total_expense_wtd']) / df['total_revenue_wtd'] * 100
            )
        
        # Flag outliers in key metrics
        for col in bed_cols + ['operating_margin_pct']:
            if col in df.columns:
                df[f'{col}_is_outlier'] = DataCleaner._flag_outliers(df[col])
        
        logger.info(f"HCRIS cleaned: {df.shape[0]} records")
        return df
    
    @staticmethod
    def clean_mortreadm(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean mortality and readmission rates
        
        Args:
            df: Raw mortality/readmission DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        df = df.copy()
        logger.info("Cleaning Mortality/Readmission data...")
        
        # Standardize provider number
        df['pn'] = df['pn'].astype(str).str.strip()
        
        # Remove rows with missing provider or year
        initial_rows = len(df)
        df = df.dropna(subset=['pn', 'year'])
        logger.info(f"Removed {initial_rows - len(df)} rows with missing pn or year")
        
        # Clinical outcome columns
        outcome_cols = [col for col in df.columns if '_rate' in col and col not in ['_denom']]
        
        # Remove rows where rates are outside plausible range
        for col in outcome_cols:
            if col in df.columns:
                df = df.loc[(df[col] >= 0) & (df[col] <= 100)]  # type: ignore
        
        # Impute missing rates with condition-specific median
        for col in outcome_cols:
            if col in df.columns:
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
        
        # Create composite outcome score
        outcome_metrics = [col for col in outcome_cols if 'mort' in col or 'readm' in col]
        if outcome_metrics:
            df['clinical_risk_score'] = df[outcome_metrics].mean(axis=1)
        
        logger.info(f"Mortality/Readmission cleaned: {df.shape[0]} records")
        return df
    
    @staticmethod
    def clean_poc(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean process of care measures
        
        Args:
            df: Raw process of care DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        df = df.copy()
        logger.info("Cleaning Process of Care data...")
        
        # Standardize provider number
        df['pn'] = df['pn'].astype(str).str.strip()
        
        # Remove rows with missing provider or year
        initial_rows = len(df)
        df = df.dropna(subset=['pn', 'year'])
        logger.info(f"Removed {initial_rows - len(df)} rows with missing pn or year")
        
        # Calculate quality measures from share columns
        share_cols = [col for col in df.columns if '_share' in col]
        for col in share_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(df[col].median())
        
        # Create composite quality score
        if share_cols:
            df['process_quality_score'] = df[share_cols].mean(axis=1)
        
        logger.info(f"Process of Care cleaned: {df.shape[0]} records")
        return df
    
    @staticmethod
    def _flag_outliers(series: pd.Series, threshold: float = OUTLIER_THRESHOLD) -> pd.Series:
        """
        Flag outliers using z-score method
        
        Args:
            series: Data series to check
            threshold: Number of standard deviations
            
        Returns:
            Boolean series indicating outliers
        """
        if series.isna().all():
            return pd.Series([False] * len(series))
        
        z_scores = np.abs((series - series.mean()) / series.std())
        return z_scores > threshold
    
    @staticmethod
    def validate_merged_data(df: pd.DataFrame) -> Dict[str, str]:
        """
        Validate merged dataset for analysis readiness
        
        Args:
            df: Merged hospital dataset
            
        Returns:
            Dictionary with validation metrics
        """
        validation = {
            'total_records': len(df),
            'unique_hospitals': df['pn'].nunique() if 'pn' in df.columns else 0,
            'year_range': (df['year'].min(), df['year'].max()) if 'year' in df.columns else None,
            'missing_pct': (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100,
            'hospitals_with_min_obs': len(
                df.groupby('pn').filter(lambda x: len(x) >= MIN_HOSPITAL_OBSERVATIONS)['pn'].unique()
            ) if 'pn' in df.columns else 0
        }
        
        return validation


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    print("Data Cleaner module loaded successfully")
