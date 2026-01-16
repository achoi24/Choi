"""IV change estimation model"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from datetime import datetime


class IVModel:
    """
    Model for estimating implied volatility changes given spot movements.
    
    Key dynamics modeled:
    1. Spot/Vol beta: IV increases when spot decreases (negative correlation)
    2. Term structure: Front-month vol moves more than back-month
    3. Skew: OTM puts see amplified IV moves on selloffs, dampened on rallies
    """
    
    def __init__(
        self,
        spot_vol_beta: float = -3.0,
        skew_factor: float = 1.0,
        term_structure_slope: float = 1.0,
        reference_tenor_days: float = 30,
    ):
        """
        Initialize IV model with parameters.
        
        Args:
            spot_vol_beta: Sensitivity of ATM vol to spot moves (typical: -2 to -5)
                          A value of -3 means 1% spot drop -> 3 vol point rise
            skew_factor: Skew dynamics multiplier (0 = parallel, >0 = steepens on selloffs)
            term_structure_slope: >1 means front-month more sensitive, <1 means flatter
            reference_tenor_days: Reference tenor for term structure adjustment
        """
        self.spot_vol_beta = spot_vol_beta
        self.skew_factor = skew_factor
        self.term_structure_slope = term_structure_slope
        self.reference_tenor_days = reference_tenor_days
    
    def estimate_atm_iv_change(
        self,
        spot_change_pct: float,
        days_to_expiry: float,
    ) -> float:
        """
        Estimate ATM IV change for a given spot move and tenor.
        
        Args:
            spot_change_pct: Spot change as decimal (e.g., -0.05 for -5%)
            days_to_expiry: Days until expiration
            
        Returns:
            Estimated IV change in vol points
        """
        # Base IV change from spot/vol beta
        base_iv_change = self.spot_vol_beta * spot_change_pct * 100  # Convert to vol points
        
        # Term structure adjustment: front-month moves more
        # sqrt(ref/dte) means shorter tenors have larger moves
        term_adjustment = np.sqrt(self.reference_tenor_days / max(days_to_expiry, 1))
        term_adjustment = term_adjustment ** self.term_structure_slope
        
        # Cap the term adjustment to avoid extreme values
        term_adjustment = np.clip(term_adjustment, 0.3, 3.0)
        
        return base_iv_change * term_adjustment
    
    def estimate_iv_change(
        self,
        spot_change_pct: float,
        moneyness: float,
        days_to_expiry: float,
    ) -> float:
        """
        Estimate IV change for a specific strike/expiry.
        
        Args:
            spot_change_pct: Spot change as decimal
            moneyness: K/S ratio (e.g., 0.9 = 10% OTM put)
            days_to_expiry: Days until expiration
            
        Returns:
            Estimated IV change in vol points
        """
        # Get ATM IV change
        atm_iv_change = self.estimate_atm_iv_change(spot_change_pct, days_to_expiry)
        
        # Skew adjustment
        # sign(spot_change) * (1 - moneyness) captures:
        # - Spot down: OTM puts (moneyness < 1) get amplified, OTM calls dampened
        # - Spot up: OTM puts get dampened, OTM calls slightly amplified
        spot_direction = np.sign(spot_change_pct) if spot_change_pct != 0 else 0
        skew_multiplier = 1 + self.skew_factor * (-spot_direction) * (1 - moneyness)
        
        # Ensure multiplier stays reasonable
        skew_multiplier = np.clip(skew_multiplier, 0.2, 3.0)
        
        return atm_iv_change * skew_multiplier
    
    def estimate_iv_changes_grid(
        self,
        spot_change_pct: float,
        moneyness_levels: np.ndarray,
        expiry_dates: pd.Index,
        reference_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Estimate IV changes for an entire grid.
        
        Returns DataFrame with same structure as vega grids.
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Calculate days to expiry for each column
        dte = {}
        for exp in expiry_dates:
            if isinstance(exp, pd.Timestamp):
                dte[exp] = max((exp - pd.Timestamp(reference_date)).days, 1)
            else:
                dte[exp] = 30
        
        # Build IV change grid
        iv_changes = pd.DataFrame(
            index=moneyness_levels,
            columns=expiry_dates,
            dtype=float
        )
        
        for moneyness in moneyness_levels:
            for exp in expiry_dates:
                iv_changes.loc[moneyness, exp] = self.estimate_iv_change(
                    spot_change_pct,
                    moneyness,
                    dte[exp]
                )
        
        return iv_changes


def create_iv_model(params: Dict) -> IVModel:
    """Factory function to create IV model from parameter dict."""
    return IVModel(
        spot_vol_beta=params.get('spot_vol_beta', -3.0),
        skew_factor=params.get('skew_factor', 1.0),
        term_structure_slope=params.get('term_structure_slope', 1.0),
        reference_tenor_days=params.get('reference_tenor_days', 30),
    )
