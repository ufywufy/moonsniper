from core.datafetch import fetch_batch_history
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import yfinance as yf
import pytz
from datetime import datetime, time
import streamlit as st
import concurrent.futures
import numpy as np  # <-- add

def fetch_infos_parallel(tickers):
    def fetch_info(tkr):
        try:
            return tkr, yf.Ticker(tkr).info
        except Exception as e:
            print(f"[INFO FAIL] {tkr}: {e}")
            return tkr, {}
    info_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        for tkr, info in executor.map(fetch_info, tickers):
            info_map[tkr] = info
    return info_map

def is_market_open():
    now = datetime.now(pytz.timezone("US/Eastern"))
    return now.weekday() < 5 and time(9, 30) <= now.time() <= time(16, 0)

@st.cache_data(ttl=60 if is_market_open() else 3600)
def build_watchlist_df(tickers: list[str]) -> pd.DataFrame:
    """Base snapshot (no session-diff moves here)."""
    hist_all = fetch_batch_history(tickers)
    info_map = fetch_infos_parallel(tickers)
    rows = []

    for tkr in tickers:
        try:
            h = hist_all.get(tkr) if isinstance(hist_all.columns, pd.MultiIndex) else hist_all
            if h is None or h.empty or len(h) < 2:
                print(f"[SKIP] No data for {tkr}")
                continue

            h = h.copy()
            h["RSI"] = RSIIndicator(h["Close"], 14).rsi()
            h["MACD_diff"] = MACD(h["Close"]).macd_diff()
            last = h.iloc[-1]

            info = info_map.get(tkr, {})
            so = info.get("sharesOutstanding")
            mcap = so * last["Close"] if so else info.get("marketCap", 0)

            rows.append({
                "Ticker":     tkr,
                "Price":      float(last["Close"]),
                "RSI":        float(last["RSI"]),
                "MACD":       float(last["MACD_diff"]),
                "Volume":     int(last["Volume"]),
                "Avg Vol":    float(h["Volume"].rolling(20).mean().iloc[-1] if len(h) >= 20 else h["Volume"].mean()),
                "Market Cap": mcap,
                "Float":      info.get("floatShares", None),
                "PE Ratio":   info.get("trailingPE", None),
                "EPS":        info.get("trailingEps", None),
                "Pct Change": float((last["Close"] / h["Close"].iloc[-2] - 1) * 100),
            })
        except Exception as e:
            print(f"[ERROR] {tkr}: {e}")
            continue

    print(f"[DONE] Fetched {len(rows)} tickers.")
    return pd.DataFrame(rows)

# ----- NEW: moves vs previous refresh snapshot (non-cached) -----

def _make_snapshot(df: pd.DataFrame) -> dict:
    """Create a lightweight baseline for next refresh."""
    cols = [c for c in ["Ticker", "Price", "Volume", "RSI"] if c in df.columns]
    if not cols:
        return {"values": {}}
    return {"values": df[cols].set_index("Ticker").to_dict(orient="index")}

def apply_refresh_moves(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds:
      - priceMove: % price change since last refresh
      - volMove:   % volume change since last refresh
      - rsiMove:   RSI points change since last refresh
    Uses st.session_state['refresh_snapshot'] as the baseline.
    """
    # ensure columns exist
    for k in ("priceMove", "volMove", "rsiMove"):
        if k not in df.columns:
            df[k] = np.nan

    snap = st.session_state.get("refresh_snapshot")
    if not snap or "values" not in snap or not snap["values"]:
        return df  # first run or no baseline

    prev = pd.DataFrame.from_dict(snap["values"], orient="index")
    m = df.merge(prev, left_on="Ticker", right_index=True, how="left", suffixes=("", "_prev"))

    # % price change
    m["priceMove"] = np.where(
        m["Price_prev"] > 0,
        100.0 * (m["Price"] - m["Price_prev"]) / m["Price_prev"],
        np.nan,
    )

    # % volume change; ignore if counter reset (current < prev)
    m["volMove"] = np.where(
        (m["Volume_prev"] > 0) & (m["Volume"] >= m["Volume_prev"]),
        100.0 * (m["Volume"] - m["Volume_prev"]) / m["Volume_prev"],
        np.nan,
    )

    # RSI point change
    m["rsiMove"] = m["RSI"] - m["RSI_prev"]

    drop_prev = [c for c in m.columns if c.endswith("_prev")]
    return m.drop(columns=drop_prev, errors="ignore")

class WatchlistDf:
    def __init__(self, path=None, tickers=None):
        if tickers is not None:
            self.wl = [t.strip().upper() for t in tickers if t.strip()]
        elif path is not None:
            with open(path) as f:
                self.wl = [
                    line.split("#")[0].strip().upper()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
        else:
            raise ValueError("Provide either a file path or a list of tickers")

    def build_df(self):
        # Base (cached)
        df = build_watchlist_df(self.wl)
        # Session-based moves (not cached)
        df = apply_refresh_moves(df)
        # Optionally update baseline here if you want (or do it in main after render)
        # st.session_state["refresh_snapshot"] = _make_snapshot(df)
        return df