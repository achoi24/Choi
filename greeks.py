"""Greeks calculations: Vanna and Volga estimation from vega grids"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple


class GreeksCalculator:
    """
    Calculate second-order Greeks (vanna, volga) from vega grids.
    
    Vanna: ∂Vega/∂Spot - estimated from vega differences across spot scenarios
    Volga: ∂Vega/∂IV - estimated using moneyness-based proxy
    """
    
    def __init__(self, volga_scalar: float = 0.5):
        """
        Initialize Greeks calculator.
        
        Args:
            volga_scalar: Scaling factor for volga estimation
        """
        self.volga_scalar = volga_scalar
    
    def estimate_vanna_from_grids(
        self,
        vega_grids: Dict[str, pd.DataFrame],
        spot_scenarios: Dict[str, float],
        current_spot: float = 100.0,
    ) -> pd.DataFrame:
        """
        Estimate vanna grid from multiple vega scenario grids.
        
        Uses central difference where possible:
        Vanna ≈ [Vega(S+ΔS) - Vega(S-ΔS)] / (2 × ΔS)
        
        Args:
            vega_grids: Dict mapping scenario names to vega DataFrames
            spot_scenarios: Dict mapping scenario names to spot changes (decimals)
            current_spot: Current spot level for scaling
            
        Returns:
            DataFrame of vanna estimates
        """
        if 'atm' not in vega_grids:
            raise ValueError("ATM vega grid required for vanna calculation")
        
        atm_grid = vega_grids['atm']
        vanna = pd.DataFrame(
            index=atm_grid.index,
            columns=atm_grid.columns,
            data=0.0
        )
        
        # Try to use symmetric scenarios for central difference
        scenario_pairs = [
            ('up_75', 'down_75', 0.15),
            ('up_50', 'down_50', 0.10),
            ('up_25', 'down_25', 0.05),
        ]
        
        for up_key, down_key, delta_spot_pct in scenario_pairs:
            if up_key in vega_grids and down_key in vega_grids:
                up_grid = vega_grids[up_key]
                down_grid = vega_grids[down_key]
                
                # Central difference
                delta_spot = delta_spot_pct * current_spot
                vanna = (up_grid - down_grid) / (2 * delta_spot)
                break
        else:
            # Fall back to one-sided difference if symmetric not available
            for scenario, spot_chg in spot_scenarios.items():
                if scenario != 'atm' and scenario in vega_grids:
                    delta_spot = spot_chg * current_spot
                    if abs(delta_spot) > 0:
                        vanna = (vega_grids[scenario] - atm_grid) / delta_spot
                    break
        
        return vanna
    
    def estimate_volga(
        self,
        vega_grid: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Estimate volga grid using moneyness-based proxy.
        
        Volga is higher for wings (far OTM options) and lower for ATM.
        Approximation: Volga ≈ Vega × (K/S - 1)² × volga_scalar
        
        This captures the convexity of vega with respect to IV for wing strikes.
        """
        volga = pd.DataFrame(
            index=vega_grid.index,
            columns=vega_grid.columns,
            dtype=float
        )
        
        for moneyness in vega_grid.index:
            # Wing factor: increases for strikes away from ATM
            wing_factor = (moneyness - 1.0) ** 2
            volga.loc[moneyness] = vega_grid.loc[moneyness] * wing_factor * self.volga_scalar
        
        return volga
    
    def estimate_volga_from_grids(
        self,
        vega_grids: Dict[str, pd.DataFrame],
        iv_changes: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """
        More sophisticated volga estimation using vega changes across IV scenarios.
        
        If we have vega at different implied spot scenarios, and those scenarios
        correspond to different IV levels, we can estimate how vega changes with IV.
        """
        if 'atm' not in vega_grids:
            raise ValueError("ATM grid required")
        
        atm_grid = vega_grids['atm']
        
        # Use multiple scenarios to estimate volga
        volga_estimates = []
        
        for scenario, grid in vega_grids.items():
            if scenario != 'atm' and scenario in iv_changes:
                iv_chg = iv_changes[scenario]
                
                # Avoid division by zero
                safe_iv_chg = iv_chg.replace(0, np.nan)
                
                # ∂Vega/∂IV ≈ ΔVega / ΔIV
                volga_est = (grid - atm_grid) / safe_iv_chg
                volga_estimates.append(volga_est)
        
        if volga_estimates:
            # Average across estimates
            volga = pd.concat(volga_estimates).groupby(level=0).mean()
            return volga.reindex(atm_grid.index)
        else:
            # Fall back to proxy method
            return self.estimate_volga(atm_grid)


def calculate_greeks(
    vega_grids: Dict[str, pd.DataFrame],
    spot_scenarios: Dict[str, float],
    volga_scalar: float = 0.5,
    current_spot: float = 100.0,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convenience function to calculate both vanna and volga.
    
    Returns:
        Tuple of (vanna_grid, volga_grid)
    """
    calc = GreeksCalculator(volga_scalar=volga_scalar)
    
    vanna = calc.estimate_vanna_from_grids(vega_grids, spot_scenarios, current_spot)
    volga = calc.estimate_volga(vega_grids.get('atm', list(vega_grids.values())[0]))
    
    return vanna, volga
