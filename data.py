import bql
import pandas as pd

bq = bql.Service()

# Example: pull SPX option chain with key fields
query = """
get(
    id,
    opt_expire_dt,
    opt_strike_px,
    opt_put_call,
    px_last,
    px_bid,
    px_ask,
    volume,
    open_int,
    impvol_mid,
    delta_mid,
    gamma_mid,
    yest_close
) for('SPX Index', type=OPT)
"""

res = bq.execute(query)
df = res[0].df()

# Compute Net = Last - YestClose
df["net"] = df["px_last"] - df["yest_close"]

df.head()

from datetime import datetime

def _format_expiry(d):
    try:
        return pd.to_datetime(d).strftime("%a %b %d %Y")
    except Exception:
        return str(d)

def pivot_cboe(df):
    calls = df[df["opt_put_call"].str.upper()=="CALL"].copy()
    puts  = df[df["opt_put_call"].str.upper()=="PUT"].copy()

    key = ["opt_expire_dt","opt_strike_px"]

    c = calls[key + ["id","px_last","net","px_bid","px_ask","volume","impvol_mid","delta_mid","gamma_mid","open_int"]]
    c.columns = key + ["Calls","Last Sale","Net","Bid","Ask","Volume","IV","Delta","Gamma","Open Interest"]

    p = puts[key + ["id","px_last","net","px_bid","px_ask","volume","impvol_mid","delta_mid","gamma_mid","open_int"]]
    p.columns = key + ["Puts","Last Sale","Net","Bid","Ask","Volume","IV","Delta","Gamma","Open Interest"]

    merged = pd.merge(c, p, on=key, how="outer")
    merged["Expiration Date"] = merged["opt_expire_dt"].apply(_format_expiry)

    out_cols = [
        "Expiration Date","Calls","Last Sale","Net","Bid","Ask","Volume","IV","Delta","Gamma","Open Interest",
        "Puts","Last Sale","Net","Bid","Ask","Volume","IV","Delta","Gamma","Open Interest"
    ]
    return merged[out_cols]

# Usage:
cboe_df = pivot_cboe(df)
cboe_df.head()
