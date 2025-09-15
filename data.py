import bql
import pandas as pd
from datetime import datetime

bq = bql.Service()

# --- Define universe: all SPX options ---
opt_univ = bql.Univ("SPX Index", typ="OPT")

# --- Define fields to pull ---
fields = {
    "bbg_ticker": bql.Function("id"),
    "expiry":     bql.Function("opt_expire_dt"),
    "strike":     bql.Function("opt_strike_px"),
    "put_call":   bql.Function("opt_put_call"),
    "px_last":    bql.Function("px_last"),
    "px_bid":     bql.Function("px_bid"),
    "px_ask":     bql.Function("px_ask"),
    "volume":     bql.Function("volume"),
    "open_int":   bql.Function("open_int"),
    "iv_mid":     bql.Function("impvol_mid"),     # if missing, try "ivol_mid"
    "delta_mid":  bql.Function("delta_mid"),      # alt: "opt_delta_mid"
    "gamma_mid":  bql.Function("gamma_mid"),      # alt: "opt_gamma_mid"
    "yest_close": bql.Function("yest_close"),
}

req = bql.Request(opt_univ, fields)
res = bq.execute(req)
df = res[0].df()

# --- Compute Net = Last - YestClose ---
df["net"] = df["px_last"] - df["yest_close"]

df.head()