"""
Data Loading Module
Handles loading, initial inspection, and basic preprocessing of raw data
"""
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import (
    HCAHPS_RAW, HCRIS_RAW, MORTREADM_RAW, POC_RAW,
    LOG_FORMAT
)

logging.basicConfig(format=LOG_FORMAT)
logger = logging.getLogger(__name__)


class DataLoader:
    """Load and provide initial inspection of healthcare datasets"""
    
    @staticmethod
    def load_stata_file(file_path: Path, verbose: bool = True) -> pd.DataFrame:
        """
        Load .dta (Stata) file
        
        Args:
            file_path: Path to the .dta file
            verbose: Print loading information
            
        Returns:
            DataFrame with loaded data
        """
        try:
            df = pd.read_stata(str(file_path))
            if verbose:
                logger.info(f"Loaded {file_path.name}: {df.shape[0]} rows × {df.shape[1]} columns")
            return df
        except Exception as e:
            logger.error(f"Error loading {file_path.name}: {str(e)}")
            raise
    
    @staticmethod
    def load_all_raw_data() -> Dict[str, pd.DataFrame]:
        """
        Load all raw datasets
        
        Returns:
            Dictionary with dataset names and DataFrames
        """
        logger.info("Loading raw datasets...")
        
        data = {
            'hcahps': DataLoader.load_stata_file(HCAHPS_RAW),
            'hcris': DataLoader.load_stata_file(HCRIS_RAW),
            'mortreadm': DataLoader.load_stata_file(MORTREADM_RAW),
            'poc': DataLoader.load_stata_file(POC_RAW)
        }
        
        logger.info(f"Loaded {len(data)} datasets successfully")
        return data
    
    @staticmethod
    def inspect_dataset(df: pd.DataFrame, name: str = "Dataset") -> None:
        """
        Print detailed inspection of dataset
        
        Args:
            df: DataFrame to inspect
            name: Name of the dataset for logging
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"INSPECTION: {name}")
        logger.info(f"{'='*80}")
        logger.info(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        logger.info(f"\nData Types:\n{df.dtypes}")
        logger.info(f"\nMissing Values:\n{df.isnull().sum()}")
        logger.info(f"\nBasic Statistics:\n{df.describe()}")
    
    @staticmethod
    def get_data_quality_report(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Generate quality report for all datasets
        
        Args:
            data: Dictionary of DataFrames
            
        Returns:
            DataFrame with quality metrics
        """
        quality_report = []
        
        for name, df in data.items():
            missing_pct = (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100
            
            quality_report.append({
                'Dataset': name,
                'Rows': df.shape[0],
                'Columns': df.shape[1],
                'Missing %': round(missing_pct, 2),
                'Memory (MB)': df.memory_usage(deep=True).sum() / 1024**2
            })
        
        return pd.DataFrame(quality_report)


if __name__ == "__main__":
    # Quick test
    logger.setLevel(logging.INFO)
    
    data = DataLoader.load_all_raw_data()
    
    for name, df in data.items():
        DataLoader.inspect_dataset(df, name)
    
    print("\nData Quality Report:")
    print(DataLoader.get_data_quality_report(data))
