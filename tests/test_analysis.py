"""
Unit tests for data cleaning and analysis modules
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))



sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_cleaner import DataCleaner


class TestDataCleaning:
    """Test data cleaning operations"""
    
    @pytest.fixture
    def sample_hcahps(self):
        """Create sample HCAHPS data"""
        return pd.DataFrame({
            'pn': ['123456', '234567', '345678'],
            'year': [2020, 2020, 2020],
            'clean_score': [2.5, np.nan, 2.8],
            'overall_score': [2.6, 2.7, 2.5],
            'recommend_score': [2.4, 2.5, 2.6]
        })
    
    def test_hcahps_cleaning_removes_missing_providers(self, sample_hcahps):
        """Test that rows with missing provider numbers are removed"""
        df = sample_hcahps.copy()
        df.loc[0, 'pn'] = None
        
        cleaned = DataCleaner.clean_hcahps(df)
        
        assert len(cleaned) == 2  # One row removed
    
    def test_hcahps_imputes_missing_scores(self, sample_hcahps):
        """Test that missing scores are imputed"""
        cleaned = DataCleaner.clean_hcahps(sample_hcahps)
        
        # Should not have NaN values in score columns
        assert not cleaned[['clean_score', 'overall_score']].isna().any().any()
    
    def test_experience_score_creation(self, sample_hcahps):
        """Test composite experience score is created"""
        cleaned = DataCleaner.clean_hcahps(sample_hcahps)
        
        assert 'experience_score' in cleaned.columns
        assert not cleaned['experience_score'].isna().any()
