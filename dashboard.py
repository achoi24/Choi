"""
Vega P&L Dashboard - Interactive Plotly Dash Application

Run with: python dashboard.py
"""

import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
from io import StringIO
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_PARAMS, PARAM_RANGES, SPOT_SCENARIOS, SCENARIO_LABELS, COLORS
from data_loader import load_vega_grids_from_dict
from pnl_engine import create_pnl_engine
from sample_data import SAMPLE_GRIDS

# ============================================================================
# INITIALIZE APP
# ============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Vega P&L Dashboard"
)

# ============================================================================
# LOAD DATA
# ============================================================================

def load_data():
    """Load vega grids from sample data or uploaded files."""
    grids = load_vega_grids_from_dict(SAMPLE_GRIDS)
    return grids

VEGA_GRIDS = load_data()

# ============================================================================
# LAYOUT COMPONENTS
# ============================================================================

def create_parameter_card():
    """Create the parameter control panel."""
    return dbc.Card([
        dbc.CardHeader(html.H5("Model Parameters", className="mb-0")),
        dbc.CardBody([
            # Spot/Vol Beta
            html.Label("Spot/Vol Beta (β)", className="mt-2"),
            html.Div([
                dcc.Slider(
                    id='beta-slider',
                    min=PARAM_RANGES['spot_vol_beta']['min'],
                    max=PARAM_RANGES['spot_vol_beta']['max'],
                    step=PARAM_RANGES['spot_vol_beta']['step'],
                    value=DEFAULT_PARAMS['spot_vol_beta'],
                    marks={i: str(i) for i in range(-5, 0)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], className="mb-3"),
            html.Small("1% spot drop → β vol point rise", className="text-muted"),
            
            # Skew Factor
            html.Label("Skew Factor", className="mt-4"),
            html.Div([
                dcc.Slider(
                    id='skew-slider',
                    min=PARAM_RANGES['skew_factor']['min'],
                    max=PARAM_RANGES['skew_factor']['max'],
                    step=PARAM_RANGES['skew_factor']['step'],
                    value=DEFAULT_PARAMS['skew_factor'],
                    marks={i: str(i) for i in range(-2, 3)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], className="mb-3"),
            html.Small("0=parallel, >0=steepens on selloffs", className="text-muted"),
            
            # Term Structure Slope
            html.Label("Term Structure Slope", className="mt-4"),
            html.Div([
                dcc.Slider(
                    id='term-slider',
                    min=PARAM_RANGES['term_structure_slope']['min'],
                    max=PARAM_RANGES['term_structure_slope']['max'],
                    step=PARAM_RANGES['term_structure_slope']['step'],
                    value=DEFAULT_PARAMS['term_structure_slope'],
                    marks={0.5: '0.5', 1: '1', 1.5: '1.5', 2: '2'},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], className="mb-3"),
            html.Small(">1=front-month more sensitive", className="text-muted"),
            
            # Volga Scalar
            html.Label("Volga Scalar", className="mt-4"),
            html.Div([
                dcc.Slider(
                    id='volga-slider',
                    min=PARAM_RANGES['volga_scalar']['min'],
                    max=PARAM_RANGES['volga_scalar']['max'],
                    step=PARAM_RANGES['volga_scalar']['step'],
                    value=DEFAULT_PARAMS['volga_scalar'],
                    marks={0: '0', 0.5: '0.5', 1: '1'},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], className="mb-3"),
            html.Small("Wing vega convexity multiplier", className="text-muted"),
        ])
    ], className="mb-4")


def create_scenario_selector():
    """Create the scenario selection panel."""
    return dbc.Card([
        dbc.CardHeader(html.H5("Scenario Selection", className="mb-0")),
        dbc.CardBody([
            dbc.RadioItems(
                id='scenario-selector',
                options=[
                    {'label': SCENARIO_LABELS[k], 'value': k} 
                    for k in ['down_75', 'down_50', 'down_25', 'atm', 'up_25', 'up_50', 'up_75']
                ],
                value='down_25',
                inline=True,
                className="scenario-radio"
            ),
        ])
    ], className="mb-4")


def create_pnl_summary_card():
    """Create the P&L summary display."""
    return dbc.Card([
        dbc.CardHeader(html.H5("P&L Summary", className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div(id='vega-pnl-display', className="pnl-metric"),
                    html.Small("Vega P&L", className="text-muted")
                ], width=3),
                dbc.Col([
                    html.Div(id='vanna-pnl-display', className="pnl-metric"),
                    html.Small("Vanna P&L", className="text-muted")
                ], width=3),
                dbc.Col([
                    html.Div(id='volga-pnl-display', className="pnl-metric"),
                    html.Small("Volga P&L", className="text-muted")
                ], width=3),
                dbc.Col([
                    html.Div(id='total-pnl-display', className="pnl-metric-total"),
                    html.Small("Total P&L", className="text-muted")
                ], width=3),
            ])
        ])
    ], className="mb-4")


# ============================================================================
# MAIN LAYOUT
# ============================================================================

app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H2("Vega P&L Projection Dashboard", className="mt-4 mb-2"),
            html.P("Interactive IV change estimation and P&L projection", className="text-muted mb-4"),
        ])
    ]),
    
    # Main content
    dbc.Row([
        # Left sidebar - Parameters
        dbc.Col([
            create_parameter_card(),
        ], width=3),
        
        # Main content area
        dbc.Col([
            create_scenario_selector(),
            create_pnl_summary_card(),
            
            # Charts row 1
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("P&L by Expiry"),
                        dbc.CardBody([
                            dcc.Graph(id='pnl-by-expiry-chart', style={'height': '350px'})
                        ])
                    ])
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Scenario Comparison"),
                        dbc.CardBody([
                            dcc.Graph(id='scenario-comparison-chart', style={'height': '350px'})
                        ])
                    ])
                ], width=6),
            ], className="mb-4"),
            
            # Charts row 2
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("P&L Heatmap (Moneyness × Expiry)"),
                        dbc.CardBody([
                            dcc.Graph(id='pnl-heatmap', style={'height': '400px'})
                        ])
                    ])
                ], width=8),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("P&L by Moneyness"),
                        dbc.CardBody([
                            dcc.Graph(id='pnl-by-moneyness-chart', style={'height': '400px'})
                        ])
                    ])
                ], width=4),
            ], className="mb-4"),
            
            # IV Changes display
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Estimated IV Changes by Tenor"),
                        dbc.CardBody([
                            dcc.Graph(id='iv-changes-chart', style={'height': '300px'})
                        ])
                    ])
                ], width=12),
            ]),
        ], width=9),
    ]),
    
    # Store for computed results
    dcc.Store(id='pnl-results-store'),
    
], fluid=True, className="dashboard-container")


# ============================================================================
# CALLBACKS
# ============================================================================

@app.callback(
    Output('pnl-results-store', 'data'),
    [Input('beta-slider', 'value'),
     Input('skew-slider', 'value'),
     Input('term-slider', 'value'),
     Input('volga-slider', 'value'),
     Input('scenario-selector', 'value')]
)
def compute_pnl(beta, skew, term_slope, volga_scalar, scenario):
    """Compute P&L for current parameters and scenario."""
    params = {
        'spot_vol_beta': beta,
        'skew_factor': skew,
        'term_structure_slope': term_slope,
        'volga_scalar': volga_scalar,
        'reference_tenor_days': 30,
    }
    
    engine = create_pnl_engine(VEGA_GRIDS, SPOT_SCENARIOS)
    
    # Calculate for selected scenario
    result = engine.calculate_pnl(scenario, params)
    
    # Calculate for all scenarios (for comparison chart)
    all_results = {}
    for s in SPOT_SCENARIOS.keys():
        r = engine.calculate_pnl(s, params)
        all_results[s] = {
            'vega_pnl': r.vega_pnl,
            'vanna_pnl': r.vanna_pnl,
            'volga_pnl': r.volga_pnl,
            'total_pnl': r.total_pnl,
        }
    
    return {
        'scenario': scenario,
        'vega_pnl': result.vega_pnl,
        'vanna_pnl': result.vanna_pnl,
        'volga_pnl': result.volga_pnl,
        'total_pnl': result.total_pnl,
        'pnl_by_expiry': result.pnl_by_expiry.to_dict(),
        'pnl_by_moneyness': result.pnl_by_moneyness.to_dict(),
        'total_pnl_grid': result.total_pnl_grid.to_dict(),
        'iv_changes': result.iv_changes.to_dict(),
        'all_scenarios': all_results,
    }


@app.callback(
    [Output('vega-pnl-display', 'children'),
     Output('vanna-pnl-display', 'children'),
     Output('volga-pnl-display', 'children'),
     Output('total-pnl-display', 'children'),
     Output('vega-pnl-display', 'style'),
     Output('vanna-pnl-display', 'style'),
     Output('volga-pnl-display', 'style'),
     Output('total-pnl-display', 'style')],
    [Input('pnl-results-store', 'data')]
)
def update_pnl_summary(data):
    """Update P&L summary display."""
    if not data:
        return ["--"] * 4 + [{}] * 4
    
    def format_pnl(val):
        if abs(val) >= 1e6:
            return f"${val/1e6:,.1f}M"
        elif abs(val) >= 1e3:
            return f"${val/1e3:,.0f}K"
        else:
            return f"${val:,.0f}"
    
    def get_style(val):
        color = COLORS['profit'] if val >= 0 else COLORS['loss']
        return {'color': color, 'fontSize': '1.5rem', 'fontWeight': 'bold'}
    
    return [
        format_pnl(data['vega_pnl']),
        format_pnl(data['vanna_pnl']),
        format_pnl(data['volga_pnl']),
        format_pnl(data['total_pnl']),
        get_style(data['vega_pnl']),
        get_style(data['vanna_pnl']),
        get_style(data['volga_pnl']),
        get_style(data['total_pnl']),
    ]


@app.callback(
    Output('pnl-by-expiry-chart', 'figure'),
    [Input('pnl-results-store', 'data')]
)
def update_expiry_chart(data):
    """Update P&L by expiry bar chart."""
    if not data:
        return go.Figure()
    
    pnl_by_expiry = pd.DataFrame(data['pnl_by_expiry'])
    
    # Convert index to strings for display
    expiry_labels = [str(pd.to_datetime(x).strftime('%b %Y')) for x in pnl_by_expiry.index]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Vega P&L',
        x=expiry_labels,
        y=pnl_by_expiry['vega_pnl'].values,
        marker_color='#3498db'
    ))
    
    fig.add_trace(go.Bar(
        name='Vanna P&L',
        x=expiry_labels,
        y=pnl_by_expiry['vanna_pnl'].values,
        marker_color='#9b59b6'
    ))
    
    fig.add_trace(go.Bar(
        name='Volga P&L',
        x=expiry_labels,
        y=pnl_by_expiry['volga_pnl'].values,
        marker_color='#e67e22'
    ))
    
    fig.update_layout(
        barmode='group',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=20, t=20, b=40),
        legend=dict(orientation='h', y=-0.2),
        xaxis_tickangle=-45,
    )
    
    return fig


@app.callback(
    Output('scenario-comparison-chart', 'figure'),
    [Input('pnl-results-store', 'data')]
)
def update_scenario_chart(data):
    """Update scenario comparison chart."""
    if not data or 'all_scenarios' not in data:
        return go.Figure()
    
    all_scenarios = data['all_scenarios']
    
    # Sort scenarios by spot change
    scenario_order = ['down_75', 'down_50', 'down_25', 'atm', 'up_25', 'up_50', 'up_75']
    scenarios = [s for s in scenario_order if s in all_scenarios]
    
    spot_changes = [SPOT_SCENARIOS[s] * 100 for s in scenarios]
    total_pnls = [all_scenarios[s]['total_pnl'] for s in scenarios]
    vega_pnls = [all_scenarios[s]['vega_pnl'] for s in scenarios]
    
    fig = go.Figure()
    
    # Total P&L line
    colors = [COLORS['profit'] if p >= 0 else COLORS['loss'] for p in total_pnls]
    
    fig.add_trace(go.Scatter(
        x=spot_changes,
        y=total_pnls,
        mode='lines+markers',
        name='Total P&L',
        line=dict(color='#ffffff', width=3),
        marker=dict(size=12, color=colors, line=dict(width=2, color='#ffffff'))
    ))
    
    fig.add_trace(go.Scatter(
        x=spot_changes,
        y=vega_pnls,
        mode='lines+markers',
        name='Vega P&L',
        line=dict(color='#3498db', width=2, dash='dash'),
        marker=dict(size=8)
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis_title='Spot Change (%)',
        yaxis_title='P&L ($)',
        legend=dict(orientation='h', y=-0.2),
    )
    
    return fig


@app.callback(
    Output('pnl-heatmap', 'figure'),
    [Input('pnl-results-store', 'data')]
)
def update_heatmap(data):
    """Update P&L heatmap."""
    if not data:
        return go.Figure()
    
    pnl_grid = pd.DataFrame(data['total_pnl_grid'])
    
    # Filter to relevant moneyness range (0.7 to 1.3)
    mask = (pnl_grid.index >= 0.7) & (pnl_grid.index <= 1.3)
    pnl_grid = pnl_grid.loc[mask]
    
    # Format labels
    expiry_labels = [str(pd.to_datetime(x).strftime('%b %y')) for x in pnl_grid.columns]
    moneyness_labels = [f"{m:.0%}" for m in pnl_grid.index]
    
    # Cap extreme values for better visualization
    z_values = pnl_grid.values
    z_cap = np.percentile(np.abs(z_values[~np.isnan(z_values)]), 95)
    z_values = np.clip(z_values, -z_cap, z_cap)
    
    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=expiry_labels,
        y=moneyness_labels,
        colorscale='RdYlGn',
        zmid=0,
        colorbar=dict(title='P&L ($)')
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=60, r=20, t=20, b=40),
        xaxis_title='Expiry',
        yaxis_title='Moneyness (K/S)',
        xaxis_tickangle=-45,
    )
    
    return fig


@app.callback(
    Output('pnl-by-moneyness-chart', 'figure'),
    [Input('pnl-results-store', 'data')]
)
def update_moneyness_chart(data):
    """Update P&L by moneyness chart."""
    if not data:
        return go.Figure()
    
    pnl_by_moneyness = pd.DataFrame(data['pnl_by_moneyness'])
    
    # Filter to relevant range
    mask = (pnl_by_moneyness.index >= 0.7) & (pnl_by_moneyness.index <= 1.3)
    pnl_by_moneyness = pnl_by_moneyness.loc[mask]
    
    moneyness_labels = [f"{m:.0%}" for m in pnl_by_moneyness.index]
    
    # Color based on P&L sign
    colors = [COLORS['profit'] if p >= 0 else COLORS['loss'] 
              for p in pnl_by_moneyness['total_pnl'].values]
    
    fig = go.Figure(go.Bar(
        x=pnl_by_moneyness['total_pnl'].values,
        y=moneyness_labels,
        orientation='h',
        marker_color=colors,
    ))
    
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=60, r=20, t=20, b=40),
        xaxis_title='Total P&L ($)',
        yaxis_title='Moneyness',
    )
    
    return fig


@app.callback(
    Output('iv-changes-chart', 'figure'),
    [Input('pnl-results-store', 'data')]
)
def update_iv_chart(data):
    """Update IV changes chart."""
    if not data:
        return go.Figure()
    
    iv_changes = pd.DataFrame(data['iv_changes'])
    
    # Select a few key moneyness levels to display
    key_levels = [0.9, 0.95, 1.0, 1.05, 1.1]
    available_levels = [l for l in key_levels if any(abs(iv_changes.index - l) < 0.03)]
    
    if not available_levels:
        available_levels = iv_changes.index[::max(1, len(iv_changes)//5)][:5].tolist()
    
    expiry_labels = [str(pd.to_datetime(x).strftime('%b %Y')) for x in iv_changes.columns]
    
    fig = go.Figure()
    
    colors = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#3498db']
    
    for i, level in enumerate(available_levels):
        # Find closest available level
        idx = (iv_changes.index - level).abs().argmin()
        actual_level = iv_changes.index[idx]
        
        fig.add_trace(go.Scatter(
            x=expiry_labels,
            y=iv_changes.loc[actual_level].values,
            mode='lines+markers',
            name=f'{actual_level:.0%} K/S',
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=6)
        ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis_title='Expiry',
        yaxis_title='IV Change (vol points)',
        legend=dict(orientation='h', y=-0.3),
        xaxis_tickangle=-45,
    )
    
    return fig


# ============================================================================
# CUSTOM CSS
# ============================================================================

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .dashboard-container {
                background-color: #1a1a2e;
                min-height: 100vh;
            }
            .card {
                background-color: #16213e;
                border: 1px solid #0f3460;
            }
            .card-header {
                background-color: #0f3460;
                border-bottom: 1px solid #0f3460;
            }
            .pnl-metric, .pnl-metric-total {
                font-size: 1.5rem;
                font-weight: bold;
            }
            .scenario-radio .form-check {
                display: inline-block;
                margin-right: 1rem;
            }
            .rc-slider-track {
                background-color: #3498db;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    print("Starting Vega P&L Dashboard...")
    print("Open http://127.0.0.1:8050 in your browser")
    app.run_server(debug=True, host='0.0.0.0', port=8050)
