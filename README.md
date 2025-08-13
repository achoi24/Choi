# Achoi24
2024 Emory University Graduate earning a BBA in Finance from Goizueta Business School. Interested in sell-side trading and quant positions, investment management, and options market making.
Served as President of Algory Capital-- largest student-led multi-strategy quantitative investment club in the South East. First campus organization with authorization to trade derivatives at Emory University.

2023 Truist Securities ST&R Institutional Equity Derivatives intern.
FX Futures and Equity CFDs Proprietary Trader @ FTMO

LinkedIn: https://www.linkedin.com/in/asher-choi107/

Project's I've completed along the way. Includes derivative models and in-house tools for Algory Capital as well as class/personal work in machine learning and neural networks. 

- Equity Options Gamma Exposure Model: used to identify concentration of gamma exposure based on held positions in the open market. Data provided by CBOE options chain. Model is used to see where banks, hedge funds, investment firms are hedging delta risk which can give indication on institutional order flow and positioning. Also can be used to identify pin risk in expiring positions. Coded in R.

- LSTM Neural Network: ACT499R: Machine Learning final project. Worked in tandem with my team to utilize academic research and create an LSTM NN that uses fundamental data to predict stock price at next quarterly earnings. Generates buy signal when predicted price is above current price and sell signal when predicted price is lower than current price. Coded in Python, neural network franework through Tensorflow Keras.

- NBA Sports Betting Model: TBA

- Chop Trading Model: Long-Only technical based strategy primarily using Kaufman Adative Moving Average (limits noise/vol) and weekly Z-Score returns & other signals/points of confirmation. Grounded in theory of mean reversion. Model trades best during choppy market conditions (Q2 2020 - Q1 2023 returns 81% with 4 losses). However, does not take many trades during periods of strong momentum/trends (took only 8 trades 2023-Q12024) Working on getting this strategy automated.




# ---------- CONFIG ----------
contract_multiplier <- 100     # SPX multiplier
scale_to_bil_per_1pct <- function(x) x / 1e9    # final y-units in $Bn per 1% move
shock_vec <- c(-0.02, -0.01, -0.005, 0, 0.005, 0.01, 0.02)  # ±2%, ±1%, ±0.5%, 0

# ---------- TIME & RATE HELPERS ----------
yearfrac_ACT365 <- function(t0, t1) as.numeric(as.Date(t1) - as.Date(t0)) / 365

# Try to use your existing calcGammaEx if present; else use local BS gamma
.has_calcGammaEx <- exists("calcGammaEx", mode = "function")

# ---------- BS GAMMA (per option) ----------
bs_gamma <- function(S, K, sigma, T, r = 0, q = 0) {
  if (any(sigma <= 0 | T <= 0)) return(rep(0, length(S)))
  d1 <- (log(S/K) + (r - q + 0.5*sigma^2)*T) / (sigma*sqrt(T))
  dens <- (1/sqrt(2*pi)) * exp(-0.5*d1^2)
  dens / (S * sigma * sqrt(T))
}

# Recompute per-row gamma * notional * OI (GEX) for either calls or puts
row_gex <- function(side, S, K, iv, T, r, q, oi) {
  if (.has_calcGammaEx) {
    # use your implementation
    return(calcGammaEx(S, K, iv, T, r, q, oi))
  } else {
    g <- bs_gamma(S, K, iv, T, r, q)
    # GEX ≈ Γ * S^2 * contract_multiplier * OI
    gex <- g * (S^2) * contract_multiplier * oi
    # sign convention: calls +, puts +
    # (use your own sign toggle elsewhere if desired)
    return(gex)
  }
}

# Total GEX at a given spot (all expiries)
total_gex_at_S <- function(dt, S, r = 0, q = 0) {
  dt[, T := pmax(1e-6, yearfrac_ACT365(Sys.Date(), ExpirationDate))]
  call_gex <- row_gex("C", S, dt$Strike, pmax(1e-6, dt$IVCall), dt$T, r, q, pmax(0, dt$OpenInterestCall))
  put_gex  <- row_gex("P", S, dt$Strike, pmax(1e-6, dt$IVPut ), dt$T, r, q, pmax(0, dt$OpenInterestPut ))
  sum(call_gex + put_gex, na.rm = TRUE)
}

# Total GEX for a single expiry at a given spot
expiry_gex_at_S <- function(dt_exp, S, r = 0, q = 0) {
  dt <- copy(dt_exp)
  dt[, T := pmax(1e-6, yearfrac_ACT365(Sys.Date(), unique(ExpirationDate)))]
  call_gex <- row_gex("C", S, dt$Strike, pmax(1e-6, dt$IVCall), dt$T, r, q, pmax(0, dt$OpenInterestCall))
  put_gex  <- row_gex("P", S, dt$Strike, pmax(1e-6, dt$IVPut ), dt$T, r, q, pmax(0, dt$OpenInterestPut ))
  sum(call_gex + put_gex, na.rm = TRUE)
}

# Find zero-gamma ("flip") by root finding on S
solve_flip <- function(f, S0, lower_mult = 0.6, upper_mult = 1.4) {
  lower <- max(1, S0 * lower_mult)
  upper <- S0 * upper_mult
  f_low <- f(lower); f_up <- f(upper)
  if (is.na(f_low) || is.na(f_up) || f_low * f_up > 0) return(NA_real_)
  uniroot(function(x) f(x), lower = lower, upper = upper)$root
}

# Pretty hover for plotly bars/points
hover_gex <- function() {
  paste0(
    "<b>%{customdata[0]}</b><br>",
    "Strike: %{x}<br>",
    "GEX: %{y:.3f} Bn / 1%<extra></extra>"
  )
}
hover_expiry <- function() {
  paste0(
    "<b>%{x}</b><br>",
    "Total GEX: %{y:.3f} Bn / 1%<extra></extra>"
  )
}