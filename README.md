# Vega P&L Projection Dashboard

An interactive dashboard for estimating implied volatility changes from spot movements and projecting P&L impacts across a portfolio of options positions.

## Overview

This dashboard allows you to:

1. **Estimate IV Changes** - Model how implied volatility shifts when spot moves, accounting for:
   - Spot/Vol correlation (beta)
   - Skew dynamics (steepening/flattening)
   - Term structure effects (front vs back month sensitivity)

2. **Project P&L** - Calculate expected P&L from three components:
   - **Vega P&L**: Direct impact from IV changes
   - **Vanna P&L**: Cross-gamma effect (Vega sensitivity to spot)
   - **Volga P&L**: Vol convexity (Vega sensitivity to IV)

3. **Analyze Scenarios** - Compare P&L across multiple spot scenarios (-7.5% to +7.5%)

## Installation

```bash
cd vega_dashboard
pip install -r requirements.txt
```

## Usage

### Running the Dashboard

```bash
python dashboard.py
```

Then open http://127.0.0.1:8050 in your browser.

### Running Tests

```bash
python test_engine.py
```

### Using as a Library

```python
from vega_dashboard import (
    load_vega_grids,
    create_pnl_engine,
    IVModel,
    DEFAULT_PARAMS,
    SPOT_SCENARIOS
)

# Load your vega grids
grids = load_vega_grids('/path/to/data/')

# Create P&L engine
engine = create_pnl_engine(grids, SPOT_SCENARIOS)

# Calculate P&L for a scenario
result = engine.calculate_pnl('down_50', DEFAULT_PARAMS)

print(f"Vega P&L: ${result.vega_pnl:,.0f}")
print(f"Vanna P&L: ${result.vanna_pnl:,.0f}")
print(f"Volga P&L: ${result.volga_pnl:,.0f}")
print(f"Total P&L: ${result.total_pnl:,.0f}")
```

## Data Format

Vega grids should be CSV files with:
- **Rows**: Moneyness levels (K/S ratio, e.g., 0.90 = 10% OTM put)
- **Columns**: Expiration dates
- **Values**: Dollar vega at each strike/expiry

Expected file naming convention:
- `SPX_atm.csv` - Current (at-the-money) vega grid
- `SPX_down_75.csv` - Vega grid if spot down 7.5%
- `SPX_down_50.csv` - Vega grid if spot down 5%
- `SPX_down_25.csv` - Vega grid if spot down 2.5%
- `SPX_up_25.csv` - Vega grid if spot up 2.5%
- `SPX_up_50.csv` - Vega grid if spot up 5%
- `SPX_up_75.csv` - Vega grid if spot up 7.5%

## Model Parameters

### Spot/Vol Beta (β)
- Controls the relationship between spot moves and ATM vol changes
- Typical values: -2 to -5 for SPX
- Example: β = -3 means 1% spot down → 3 vol point increase

### Skew Factor
- Controls how skew responds to spot moves
- 0 = parallel vol shift (no skew dynamics)
- \>0 = skew steepens on selloffs, flattens on rallies
- <0 = inverted behavior (unusual)
- Typical values: 0.5 to 1.5 for SPX

### Term Structure Slope
- Controls relative sensitivity of front vs back month
- \>1 = front month moves more than back month
- <1 = flatter response across tenors
- 1 = proportional to sqrt(reference_tenor/DTE)

### Volga Scalar
- Controls magnitude of volga (vega convexity) effect
- Higher values increase wing sensitivity to vol-of-vol
- Typical values: 0.3 to 0.7

## Architecture

```
vega_dashboard/
├── config.py          # Default parameters and constants
├── data_loader.py     # CSV parsing and data loading
├── iv_model.py        # IV change estimation model
├── greeks.py          # Vanna and volga calculations  
├── pnl_engine.py      # P&L calculation engine
├── dashboard.py       # Plotly Dash web application
├── sample_data.py     # Embedded sample data
├── test_engine.py     # Test suite
└── requirements.txt   # Python dependencies
```

## Methodology

### IV Change Estimation

```
ΔIV(K/S, τ) = ΔIV_ATM × skew_multiplier × term_adjustment

Where:
  ΔIV_ATM = β × (ΔS/S) × 100
  skew_multiplier = 1 + skew_factor × (-sign(ΔS)) × (1 - K/S)
  term_adjustment = (τ_ref / τ)^(term_slope/2)
```

### P&L Components

```
P&L_total = P&L_vega + P&L_vanna + P&L_volga

Where:
  P&L_vega  = Σ Vega × ΔIV
  P&L_vanna = Σ Vanna × ΔS × ΔIV
  P&L_volga = Σ 0.5 × Volga × (ΔIV)²
```

## License

Proprietary - Internal use only.
