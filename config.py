"""Configuration and default parameters for Vega P&L Dashboard"""

# Default model parameters
DEFAULT_PARAMS = {
    'spot_vol_beta': -3.0,      # Typical SPX: -2 to -5
    'skew_factor': 1.0,          # 0 = parallel shift, >0 = steepens on selloffs
    'term_structure_slope': 1.0, # >1 = front-month moves more, <1 = flatter response
    'volga_scalar': 0.5,         # Volga sensitivity multiplier
    'reference_tenor_days': 30,  # Reference tenor for term structure adjustment
}

# Parameter ranges for sliders
PARAM_RANGES = {
    'spot_vol_beta': {'min': -5.0, 'max': -1.0, 'step': 0.1},
    'skew_factor': {'min': -2.0, 'max': 2.0, 'step': 0.1},
    'term_structure_slope': {'min': 0.5, 'max': 2.0, 'step': 0.1},
    'volga_scalar': {'min': 0.0, 'max': 1.0, 'step': 0.05},
}

# Spot scenarios
SPOT_SCENARIOS = {
    'down_75': -0.075,
    'down_50': -0.05,
    'down_25': -0.025,
    'atm': 0.0,
    'up_25': 0.025,
    'up_50': 0.05,
    'up_75': 0.075,
}

# Display labels for scenarios
SCENARIO_LABELS = {
    'down_75': '-7.5%',
    'down_50': '-5.0%',
    'down_25': '-2.5%',
    'atm': 'ATM',
    'up_25': '+2.5%',
    'up_50': '+5.0%',
    'up_75': '+7.5%',
}

# Color scheme
COLORS = {
    'profit': '#2ECC71',
    'loss': '#E74C3C',
    'neutral': '#3498DB',
    'background': '#1a1a2e',
    'card_bg': '#16213e',
    'text': '#ffffff',
    'grid': '#0f3460',
}
