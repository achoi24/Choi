"""P&L calculation engine for vega projections"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    from .iv_model import IVModel, create_iv_model
    from .greeks import GreeksCalculator
except ImportError:
    from iv_model import IVModel, create_iv_model
    from greeks import GreeksCalculator


@dataclass
class PnLResult:
    """Container for P&L calculation results."""
    vega_pnl: float
    vanna_pnl: float
    volga_pnl: float
    total_pnl: float
    
    # Detailed breakdowns
    vega_pnl_grid: pd.DataFrame
    vanna_pnl_grid: pd.DataFrame
    volga_pnl_grid: pd.DataFrame
    total_pnl_grid: pd.DataFrame
    
    # IV changes used
    iv_changes: pd.DataFrame
    
    # By expiry aggregation
    pnl_by_expiry: pd.DataFrame
    
    # By moneyness aggregation
    pnl_by_moneyness: pd.DataFrame


class PnLEngine:
    """
    Engine for calculating P&L projections across spot/vol scenarios.
    
    P&L Components:
    1. Vega P&L = Vega × ΔIV
    2. Vanna P&L = Vanna × ΔS × ΔIV (cross-gamma effect)
    3. Volga P&L = 0.5 × Volga × (ΔIV)² (vol convexity)
    """
    
    def __init__(
        self,
        vega_grids: Dict[str, pd.DataFrame],
        spot_scenarios: Dict[str, float],
        reference_date: Optional[datetime] = None,
    ):
        """
        Initialize P&L engine.
        
        Args:
            vega_grids: Dict of scenario name -> vega DataFrame
            spot_scenarios: Dict of scenario name -> spot change (decimal)
            reference_date: Reference date for DTE calculations
        """
        self.vega_grids = vega_grids
        self.spot_scenarios = spot_scenarios
        self.reference_date = reference_date or datetime.now()
        
        # Validate we have ATM grid
        if 'atm' not in vega_grids:
            raise ValueError("ATM vega grid is required")
        
        self.atm_grid = vega_grids['atm']
        self.moneyness_levels = self.atm_grid.index.values
        self.expiry_dates = self.atm_grid.columns
    
    def calculate_pnl(
        self,
        scenario: str,
        params: Dict,
        current_spot: float = 100.0,
    ) -> PnLResult:
        """
        Calculate full P&L breakdown for a given scenario.
        
        Args:
            scenario: Scenario name (e.g., 'down_75', 'up_25')
            params: Model parameters dict
            current_spot: Current spot price for scaling
            
        Returns:
            PnLResult with all P&L components
        """
        spot_change = self.spot_scenarios.get(scenario, 0.0)
        
        # Get the vega grid for this scenario (or use ATM if not available)
        vega_grid = self.vega_grids.get(scenario, self.atm_grid)
        
        # Create IV model and estimate IV changes
        iv_model = create_iv_model(params)
        iv_changes = iv_model.estimate_iv_changes_grid(
            spot_change,
            self.moneyness_levels,
            self.expiry_dates,
            self.reference_date
        )
        
        # Calculate Greeks
        greeks_calc = GreeksCalculator(volga_scalar=params.get('volga_scalar', 0.5))
        vanna_grid = greeks_calc.estimate_vanna_from_grids(
            self.vega_grids,
            self.spot_scenarios,
            current_spot
        )
        volga_grid = greeks_calc.estimate_volga(self.atm_grid)
        
        # Calculate P&L components
        # 1. Vega P&L = Vega × ΔIV
        vega_pnl_grid = vega_grid * iv_changes
        
        # 2. Vanna P&L = Vanna × ΔS × ΔIV
        delta_spot = spot_change * current_spot
        vanna_pnl_grid = vanna_grid * delta_spot * iv_changes
        
        # 3. Volga P&L = 0.5 × Volga × (ΔIV)²
        volga_pnl_grid = 0.5 * volga_grid * (iv_changes ** 2)
        
        # Total P&L grid
        total_pnl_grid = vega_pnl_grid + vanna_pnl_grid + volga_pnl_grid
        
        # Aggregate totals
        vega_pnl = vega_pnl_grid.values.sum()
        vanna_pnl = vanna_pnl_grid.values.sum()
        volga_pnl = volga_pnl_grid.values.sum()
        total_pnl = total_pnl_grid.values.sum()
        
        # Aggregate by expiry
        pnl_by_expiry = pd.DataFrame({
            'vega_pnl': vega_pnl_grid.sum(axis=0),
            'vanna_pnl': vanna_pnl_grid.sum(axis=0),
            'volga_pnl': volga_pnl_grid.sum(axis=0),
            'total_pnl': total_pnl_grid.sum(axis=0),
        })
        
        # Aggregate by moneyness
        pnl_by_moneyness = pd.DataFrame({
            'vega_pnl': vega_pnl_grid.sum(axis=1),
            'vanna_pnl': vanna_pnl_grid.sum(axis=1),
            'volga_pnl': volga_pnl_grid.sum(axis=1),
            'total_pnl': total_pnl_grid.sum(axis=1),
        })
        
        return PnLResult(
            vega_pnl=vega_pnl,
            vanna_pnl=vanna_pnl,
            volga_pnl=volga_pnl,
            total_pnl=total_pnl,
            vega_pnl_grid=vega_pnl_grid,
            vanna_pnl_grid=vanna_pnl_grid,
            volga_pnl_grid=volga_pnl_grid,
            total_pnl_grid=total_pnl_grid,
            iv_changes=iv_changes,
            pnl_by_expiry=pnl_by_expiry,
            pnl_by_moneyness=pnl_by_moneyness,
        )
    
    def calculate_all_scenarios(
        self,
        params: Dict,
        current_spot: float = 100.0,
    ) -> Dict[str, PnLResult]:
        """Calculate P&L for all available scenarios."""
        results = {}
        for scenario in self.spot_scenarios.keys():
            results[scenario] = self.calculate_pnl(scenario, params, current_spot)
        return results
    
    def get_scenario_summary(
        self,
        params: Dict,
        current_spot: float = 100.0,
    ) -> pd.DataFrame:
        """
        Get summary table of P&L across all scenarios.
        
        Returns DataFrame with scenarios as rows and P&L components as columns.
        """
        all_results = self.calculate_all_scenarios(params, current_spot)
        
        summary_data = []
        for scenario, result in all_results.items():
            summary_data.append({
                'scenario': scenario,
                'spot_change': self.spot_scenarios[scenario],
                'vega_pnl': result.vega_pnl,
                'vanna_pnl': result.vanna_pnl,
                'volga_pnl': result.volga_pnl,
                'total_pnl': result.total_pnl,
            })
        
        df = pd.DataFrame(summary_data)
        df = df.sort_values('spot_change')
        return df


def create_pnl_engine(
    vega_grids: Dict[str, pd.DataFrame],
    spot_scenarios: Optional[Dict[str, float]] = None,
    reference_date: Optional[datetime] = None,
) -> PnLEngine:
    """Factory function to create P&L engine."""
    if spot_scenarios is None:
        spot_scenarios = {
            'down_75': -0.075,
            'down_50': -0.05,
            'down_25': -0.025,
            'atm': 0.0,
            'up_25': 0.025,
            'up_50': 0.05,
            'up_75': 0.075,
        }
    
    return PnLEngine(vega_grids, spot_scenarios, reference_date)
