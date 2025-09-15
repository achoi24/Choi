#!/usr/bin/env python3
"""
Fetch SPX options quote data from Bloomberg and emit a CSV that mirrors the CBOE-style layout.

Two backends are supported:
  1) "pdblp" (Bloomberg Open API via Desktop/Server API) — requires `pdblp` and a logged-in Terminal.
  2) "bql"   (BQuant/Bloomberg Query Language) — requires a BQuant workspace with `bql` available.

Output columns are aligned to a common CBOE download format:
  ["Expiration Date","Calls","Last Sale","Net","Bid","Ask","Volume","IV","Delta","Gamma","Open Interest",
   "Puts","Last Sale","Net","Bid","Ask","Volume","IV","Delta","Gamma","Open Interest"]

Notes & caveats:
- Field names for greeks/IV can differ by entitlement/version. The default mappings below work in many setups;
  adjust `FIELD_MAP` if your terminal uses different names (e.g., OPT_DELTA_MID vs DELTA_MID, IMPVOL_MID vs IVOL_MID).
- "Net" is computed as PX_LAST - YEST_CLOSE (or 0.0 if YEST_CLOSE is not returned).
- Weekly/Monthly options are included. Override filters if you want only certain expirations/tenors.
- For historical-on-date chains, you will likely need a Bloomberg history entitlement or OVX/OVME with DSS; this
  script focuses on current chain snapshot. Extend as needed.

Usage
-----
$ python spx_from_bloomberg.py --backend pdblp --out spx_quotedata_bbg.csv
# or
$ python spx_from_bloomberg.py --backend bql --out spx_quotedata_bbg.csv
"""
import argparse
import sys
import pandas as pd
from datetime import datetime

UNDERLYING = "SPX Index"  # Bloomberg ticker for S&P 500 index
OUTPUT_COLUMNS = [
    "Expiration Date","Calls","Last Sale","Net","Bid","Ask","Volume","IV","Delta","Gamma","Open Interest",
    "Puts","Last Sale","Net","Bid","Ask","Volume","IV","Delta","Gamma","Open Interest"
]

FIELD_MAP = {
    "px_last": "PX_LAST",
    "px_bid": "PX_BID",
    "px_ask": "PX_ASK",
    "volume": "VOLUME",
    "open_int": "OPEN_INT",
    "iv_mid": "IMPVOL_MID",        # Alternatives: IVOL_MID, OPT_IMPLIED_VOLATILITY_MID
    "delta_mid": "DELTA_MID",      # Alternative: OPT_DELTA_MID
    "gamma_mid": "GAMMA_MID",      # Alternative: OPT_GAMMA_MID
    "yest_close": "YEST_CLOSE",
    "strike": "OPT_STRIKE_PX",
    "put_call": "OPT_PUT_CALL",
    "expiry": "OPT_EXPIRE_DT",
    "ticker": "TICKER"
}

def _format_expiry(d):
    """Format a Bloomberg date as CBOE's 'Thu May 22 2025' style (Day Mon DD YYYY)."""
    if pd.isna(d):
        return ""
    if isinstance(d, (int, float)):
        s = str(int(d))
        try:
            dt = datetime.strptime(s, "%Y%m%d")
        except Exception:
            dt = pd.to_datetime(d)
    elif isinstance(d, str):
        try:
            dt = datetime.strptime(d[:10], "%Y-%m-%d")
        except Exception:
            try:
                dt = datetime.strptime(d, "%Y%m%d")
            except Exception:
                dt = pd.to_datetime(d)
    else:
        dt = pd.to_datetime(d)
    return dt.strftime("%a %b %d %Y")

def _safe_net(px_last, yest_close):
    try:
        return float(px_last) - float(yest_close)
    except Exception:
        return 0.0

def _pivot_calls_puts(df):
    """
    Merge call/put quotes by expiry+strike into the CBOE mirrored row format.
    Assumes df has standardized columns per FIELD_MAP plus a 'bbg_ticker' column.
    """
    calls = df[df['put_call'].astype(str).str.upper().eq('CALL')].copy()
    puts  = df[df['put_call'].astype(str).str.upper().eq('PUT')].copy()

    key_cols = ['expiry','strike']
    call_cols = {
        "Calls": "bbg_ticker",
        "Last Sale": "px_last",
        "Net": "net",
        "Bid": "px_bid",
        "Ask": "px_ask",
        "Volume": "volume",
        "IV": "iv_mid",
        "Delta": "delta_mid",
        "Gamma": "gamma_mid",
        "Open Interest": "open_int"
    }
    put_cols = {
        "Puts": "bbg_ticker",
        "Last Sale": "px_last",
        "Net": "net",
        "Bid": "px_bid",
        "Ask": "px_ask",
        "Volume": "volume",
        "IV": "iv_mid",
        "Delta": "delta_mid",
        "Gamma": "gamma_mid",
        "Open Interest": "open_int"
    }

    calls_small = calls[key_cols + list(call_cols.values())].copy()
    calls_small.columns = key_cols + list(call_cols.keys())

    puts_small = puts[key_cols + list(put_cols.values())].copy()
    puts_small.columns = key_cols + list(put_cols.keys())

    merged = pd.merge(calls_small, puts_small, on=key_cols, how="outer")

    merged["Expiration Date"] = merged["expiry"].apply(_format_expiry)
    merged.drop(columns=["expiry"], inplace=True)

    out = merged[["Expiration Date","Calls","Last Sale","Net","Bid","Ask","Volume","IV","Delta","Gamma","Open Interest",
                  "Puts","Last Sale","Net","Bid","Ask","Volume","IV","Delta","Gamma","Open Interest"]].copy()

    out["__sort_expiry"] = pd.to_datetime(merged["Expiration Date"])
    out["__sort_strike"] = merged["strike"].astype(float)
    out = out.sort_values(["__sort_expiry","__sort_strike"], kind="mergesort").drop(columns=["__sort_expiry","__sort_strike"])
    return out

def fetch_with_pdblp():
    import pdblp
    con = pdblp.BCon(timeout=30000)
    con.start()

    # 1) Option chain tickers
    # Try CHAIN_TICKERS first
    chain = con.ref(UNDERLYING, ["CHAIN_TICKERS"])

    tickers = []
    if "chain_tickers" in chain.columns:
        for v in chain["chain_tickers"].dropna():
            if isinstance(v, list): tickers.extend(v)
            elif isinstance(v, str): tickers.append(v)

    if not tickers:
        raise RuntimeError("No option tickers returned. Consider using a bsrch query or check entitlements.")

    # 2) Pull reference fields (chunk to avoid payload limits)
    fields = [
        FIELD_MAP["px_last"], FIELD_MAP["px_bid"], FIELD_MAP["px_ask"],
        FIELD_MAP["volume"], FIELD_MAP["open_int"],
        FIELD_MAP["iv_mid"], FIELD_MAP["delta_mid"], FIELD_MAP["gamma_mid"],
        FIELD_MAP["yest_close"],
        FIELD_MAP["strike"], FIELD_MAP["put_call"], FIELD_MAP["expiry"],
    ]

    rows = []
    chunk = 300
    for i in range(0, len(tickers), chunk):
        tks = tickers[i:i+chunk]
        ref = con.ref(tks, fields)
        rename_map = {FIELD_MAP["px_last"]: "px_last",
                      FIELD_MAP["px_bid"]: "px_bid",
                      FIELD_MAP["px_ask"]: "px_ask",
                      FIELD_MAP["volume"]: "volume",
                      FIELD_MAP["open_int"]: "open_int",
                      FIELD_MAP["iv_mid"]: "iv_mid",
                      FIELD_MAP["delta_mid"]: "delta_mid",
                      FIELD_MAP["gamma_mid"]: "gamma_mid",
                      FIELD_MAP["yest_close"]: "yest_close",
                      FIELD_MAP["strike"]: "strike",
                      FIELD_MAP["put_call"]: "put_call",
                      FIELD_MAP["expiry"]: "expiry"}
        sub = ref.rename(columns=rename_map).copy()
        sub["bbg_ticker"] = sub.index
        sub["net"] = [ _safe_net(pl, yc) for pl, yc in zip(sub["px_last"], sub["yest_close"]) ]
        rows.append(sub[["bbg_ticker","px_last","px_bid","px_ask","volume","open_int","iv_mid","delta_mid","gamma_mid","yest_close","strike","put_call","expiry","net"]])

    df = pd.concat(rows, ignore_index=True)
    return df

def fetch_with_bql():
    import bql
    bq = bql.Service()
    chain = bq.chains(UNDERLYING, "OPT")

    fields = {
        "px_last": bql.Function(FIELD_MAP["px_last"]),
        "px_bid":  bql.Function(FIELD_MAP["px_bid"]),
        "px_ask":  bql.Function(FIELD_MAP["px_ask"]),
        "volume":  bql.Function(FIELD_MAP["volume"]),
        "open_int":bql.Function(FIELD_MAP["open_int"]),
        "iv_mid":  bql.Function(FIELD_MAP["iv_mid"]),
        "delta_mid": bql.Function(FIELD_MAP["delta_mid"]),
        "gamma_mid": bql.Function(FIELD_MAP["gamma_mid"]),
        "yest_close": bql.Function(FIELD_MAP["yest_close"]),
        "strike": bql.Function(FIELD_MAP["strike"]),
        "put_call": bql.Function(FIELD_MAP["put_call"]),
        "expiry": bql.Function(FIELD_MAP["expiry"]),
        "bbg_ticker": bql.Function("id()")
    }
    req = bql.Request(chain, fields)
    res = bq.execute(req)
    df = res[0].df()
    df["net"] = df.apply(lambda r: _safe_net(r["px_last"], r["yest_close"]), axis=1)
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["pdblp","bql"], default="pdblp")
    ap.add_argument("--out", default="spx_quotedata_bbg.csv")
    args = ap.parse_args()

    if args.backend == "pdblp":
        df = fetch_with_pdblp()
    else:
        df = fetch_with_bql()

    out = _pivot_calls_puts(df)
    out = out[OUTPUT_COLUMNS]
    out.to_csv(args.out, index=False)
    print(f"Wrote {len(out):,} rows to {args.out}")

if __name__ == "__main__":
    sys.exit(main())
