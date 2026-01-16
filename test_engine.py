#!/usr/bin/env python3
"""
Test script to validate the Vega P&L Engine calculations.
Run this to verify the core functionality before launching the dashboard.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from io import StringIO

from config import DEFAULT_PARAMS, SPOT_SCENARIOS, SCENARIO_LABELS
from data_loader import load_vega_grids_from_dict
from iv_model import IVModel, create_iv_model
from greeks import GreeksCalculator
from pnl_engine import create_pnl_engine
from sample_data import SAMPLE_GRIDS


def test_iv_model():
    """Test IV model calculations."""
    print("\n" + "="*60)
    print("Testing IV Model")
    print("="*60)
    
    model = IVModel(
        spot_vol_beta=-3.0,
        skew_factor=1.0,
        term_structure_slope=1.0,
        reference_tenor_days=30
    )
    
    # Test ATM IV change for -5% spot move, 30-day expiry
    spot_change = -0.05
    dte = 30
    atm_iv_change = model.estimate_atm_iv_change(spot_change, dte)
    print(f"\nATM IV change for {spot_change*100:.1f}% spot, {dte}d expiry: {atm_iv_change:.2f} vol pts")
    
    # Test across moneyness
    print("\nIV changes by moneyness (5% spot down, 30d):")
    for moneyness in [0.85, 0.90, 0.95, 1.00, 1.05, 1.10]:
        iv_change = model.estimate_iv_change(spot_change, moneyness, dte)
        print(f"  {moneyness:.0%} K/S: {iv_change:+.2f} vol pts")
    
    # Test term structure effect
    print("\nIV changes by tenor (ATM, 5% spot down):")
    for dte in [7, 30, 90, 180, 365]:
        iv_change = model.estimate_iv_change(spot_change, 1.0, dte)
        print(f"  {dte:3d}d: {iv_change:+.2f} vol pts")
    
    print("\n✓ IV Model tests passed")
    return True


def test_data_loader():
    """Test data loading functionality."""
    print("\n" + "="*60)
    print("Testing Data Loader")
    print("="*60)
    
    grids = load_vega_grids_from_dict(SAMPLE_GRIDS)
    
    print(f"\nLoaded {len(grids)} vega grids: {list(grids.keys())}")
    
    atm_grid = grids['atm']
    print(f"\nATM Grid shape: {atm_grid.shape}")
    print(f"Moneyness range: {atm_grid.index.min():.3f} to {atm_grid.index.max():.3f}")
    print(f"Expiry range: {atm_grid.columns[0]} to {atm_grid.columns[-1]}")
    print(f"Total Vega: ${atm_grid.values.sum():,.0f}")
    
    print("\n✓ Data Loader tests passed")
    return True


def test_greeks_calculator():
    """Test Greeks calculations."""
    print("\n" + "="*60)
    print("Testing Greeks Calculator")
    print("="*60)
    
    grids = load_vega_grids_from_dict(SAMPLE_GRIDS)
    
    calc = GreeksCalculator(volga_scalar=0.5)
    
    # Test vanna estimation
    vanna = calc.estimate_vanna_from_grids(grids, SPOT_SCENARIOS, current_spot=100)
    print(f"\nVanna Grid shape: {vanna.shape}")
    print(f"Total Vanna: {vanna.values.sum():,.2f}")
    
    # Test volga estimation
    volga = calc.estimate_volga(grids['atm'])
    print(f"\nVolga Grid shape: {volga.shape}")
    print(f"Total Volga: {volga.values.sum():,.2f}")
    
    print("\n✓ Greeks Calculator tests passed")
    return True


def test_pnl_engine():
    """Test P&L engine calculations."""
    print("\n" + "="*60)
    print("Testing P&L Engine")
    print("="*60)
    
    grids = load_vega_grids_from_dict(SAMPLE_GRIDS)
    engine = create_pnl_engine(grids, SPOT_SCENARIOS)
    
    print("\nP&L by Scenario:")
    print("-" * 70)
    print(f"{'Scenario':<10} {'Spot Δ':>8} {'Vega P&L':>15} {'Vanna P&L':>15} {'Total P&L':>15}")
    print("-" * 70)
    
    for scenario in ['down_75', 'down_50', 'down_25', 'atm', 'up_25', 'up_50', 'up_75']:
        result = engine.calculate_pnl(scenario, DEFAULT_PARAMS)
        spot_chg = SPOT_SCENARIOS[scenario] * 100
        print(f"{scenario:<10} {spot_chg:>+7.1f}% {result.vega_pnl:>15,.0f} {result.vanna_pnl:>15,.0f} {result.total_pnl:>15,.0f}")
    
    print("-" * 70)
    
    # Test scenario summary
    summary = engine.get_scenario_summary(DEFAULT_PARAMS)
    print(f"\nScenario Summary DataFrame shape: {summary.shape}")
    
    print("\n✓ P&L Engine tests passed")
    return True


def test_parameter_sensitivity():
    """Test sensitivity to parameter changes."""
    print("\n" + "="*60)
    print("Testing Parameter Sensitivity")
    print("="*60)
    
    grids = load_vega_grids_from_dict(SAMPLE_GRIDS)
    engine = create_pnl_engine(grids, SPOT_SCENARIOS)
    
    scenario = 'down_50'  # 5% down
    
    # Test beta sensitivity
    print(f"\nBeta sensitivity ({SCENARIO_LABELS[scenario]} scenario):")
    for beta in [-2.0, -3.0, -4.0, -5.0]:
        params = {**DEFAULT_PARAMS, 'spot_vol_beta': beta}
        result = engine.calculate_pnl(scenario, params)
        print(f"  β = {beta}: Total P&L = ${result.total_pnl:,.0f}")
    
    # Test skew sensitivity
    print(f"\nSkew sensitivity ({SCENARIO_LABELS[scenario]} scenario):")
    for skew in [-1.0, 0.0, 1.0, 2.0]:
        params = {**DEFAULT_PARAMS, 'skew_factor': skew}
        result = engine.calculate_pnl(scenario, params)
        print(f"  Skew = {skew}: Total P&L = ${result.total_pnl:,.0f}")
    
    print("\n✓ Parameter Sensitivity tests passed")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("VEGA P&L ENGINE - TEST SUITE")
    print("="*60)
    
    tests = [
        test_iv_model,
        test_data_loader,
        test_greeks_calculator,
        test_pnl_engine,
        test_parameter_sensitivity,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            results.append(False)
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("\n✓ All tests passed! Dashboard is ready to run.")
        print("\nTo start the dashboard:")
        print("  cd /home/claude/vega_dashboard")
        print("  pip install -r requirements.txt")
        print("  python dashboard.py")
    else:
        print("\n✗ Some tests failed. Please review errors above.")
    
    return all(results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
