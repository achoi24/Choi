"""Vega P&L Dashboard - IV projection and P&L calculation toolkit"""

from .config import DEFAULT_PARAMS, PARAM_RANGES, SPOT_SCENARIOS, SCENARIO_LABELS, COLORS
from .data_loader import parse_vega_grid, load_vega_grids, load_vega_grids_from_dict
from .iv_model import IVModel, create_iv_model
from .greeks import GreeksCalculator, calculate_greeks
from .pnl_engine import PnLEngine, PnLResult, create_pnl_engine

__version__ = '1.0.0'
__all__ = [
    'DEFAULT_PARAMS',
    'PARAM_RANGES', 
    'SPOT_SCENARIOS',
    'SCENARIO_LABELS',
    'COLORS',
    'parse_vega_grid',
    'load_vega_grids',
    'load_vega_grids_from_dict',
    'IVModel',
    'create_iv_model',
    'GreeksCalculator',
    'calculate_greeks',
    'PnLEngine',
    'PnLResult',
    'create_pnl_engine',
]
