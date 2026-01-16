"""Data loader for vega grid CSV files"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


def parse_vega_grid(csv_path: str) -> pd.DataFrame:
    """
    Parse a vega grid CSV file into a structured DataFrame.
    
    Returns DataFrame with:
    - Index: moneyness levels (K/S ratio)
    - Columns: expiration dates
    - Values: vega exposure in dollars
    """
    df = pd.read_csv(csv_path, index_col=0)
    
    # Remove TOTAL column if present
    if 'TOTAL' in df.columns:
        df = df.drop(columns=['TOTAL'])
    
    # Remove summary row (empty index)
    df = df[df.index.notna()]
    
    # Convert index to float (moneyness)
    df.index = df.index.astype(float)
    df.index.name = 'moneyness'
    
    # Parse column names to datetime
    new_cols = []
    for col in df.columns:
        try:
            dt = pd.to_datetime(col)
            new_cols.append(dt)
        except:
            new_cols.append(col)
    df.columns = new_cols
    
    # Ensure all values are numeric
    df = df.apply(pd.to_numeric, errors='coerce')
    
    return df


def load_vega_grids(data_dir: str) -> Dict[str, pd.DataFrame]:
    """
    Load all vega grid files from a directory.
    
    Expected naming convention:
    - SPX_atm.csv
    - SPX_down_75.csv, SPX_down_50.csv, SPX_down_25.csv
    - SPX_up_25.csv, SPX_up_50.csv, SPX_up_75.csv
    
    Returns dict mapping scenario names to DataFrames.
    """
    grids = {}
    data_path = Path(data_dir)
    
    # Map file patterns to scenario names
    file_patterns = {
        'atm': ['SPX_atm.csv', 'spx_atm.csv'],
        'down_75': ['SPX_down_75.csv', 'spx_down_75.csv'],
        'down_50': ['SPX_down_50.csv', 'spx_down_50.csv'],
        'down_25': ['SPX_down_25.csv', 'spx_down_25.csv'],
        'up_25': ['SPX_up_25.csv', 'spx_up_25.csv'],
        'up_50': ['SPX_up_50.csv', 'spx_up_50.csv'],
        'up_75': ['SPX_up_75.csv', 'spx_up_75.csv'],
    }
    
    for scenario, patterns in file_patterns.items():
        for pattern in patterns:
            file_path = data_path / pattern
            if file_path.exists():
                grids[scenario] = parse_vega_grid(str(file_path))
                break
    
    return grids


def load_vega_grids_from_dict(csv_strings: Dict[str, str]) -> Dict[str, pd.DataFrame]:
    """
    Load vega grids from CSV string content (for embedded data).
    """
    from io import StringIO
    
    grids = {}
    for scenario, csv_content in csv_strings.items():
        df = pd.read_csv(StringIO(csv_content), index_col=0)
        
        if 'TOTAL' in df.columns:
            df = df.drop(columns=['TOTAL'])
        
        df = df[df.index.notna()]
        df.index = df.index.astype(float)
        df.index.name = 'moneyness'
        
        new_cols = []
        for col in df.columns:
            try:
                dt = pd.to_datetime(col)
                new_cols.append(dt)
            except:
                new_cols.append(col)
        df.columns = new_cols
        
        df = df.apply(pd.to_numeric, errors='coerce')
        grids[scenario] = df
    
    return grids


def calculate_days_to_expiry(expiry_dates: pd.Index, reference_date: Optional[datetime] = None) -> pd.Series:
    """Calculate days to expiry for each expiration date."""
    if reference_date is None:
        reference_date = datetime.now()
    
    dte = pd.Series(index=expiry_dates, dtype=float)
    for exp in expiry_dates:
        if isinstance(exp, pd.Timestamp):
            dte[exp] = max((exp - pd.Timestamp(reference_date)).days, 1)
        else:
            dte[exp] = 30  # Default fallback
    
    return dte


def get_grid_summary(grid: pd.DataFrame) -> dict:
    """Get summary statistics for a vega grid."""
    return {
        'total_vega': grid.values.sum(),
        'max_vega': grid.values.max(),
        'min_vega': grid.values.min(),
        'num_strikes': len(grid.index),
        'num_expiries': len(grid.columns),
        'expiry_range': (grid.columns.min(), grid.columns.max()),
        'moneyness_range': (grid.index.min(), grid.index.max()),
    }
