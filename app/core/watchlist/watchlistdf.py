from core.datafetch import fetch_batch_history
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import yfinance as yf
import pytz
from datetime import datetime, time
import streamlit as st
import concurrent.futures

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
    hist_all = fetch_batch_history(tickers)
    info_map = fetch_infos_parallel(tickers)
    rows = []

    for tkr in tickers:
        try:
            h = None
            if isinstance(hist_all.columns, pd.MultiIndex):
                h = hist_all.get(tkr)
            else:
                h = hist_all

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
                "Price":      last["Close"],
                "RSI":        last["RSI"],
                "MACD":       last["MACD_diff"],
                "Volume":     last["Volume"],
                "Avg Vol":    h["Volume"].rolling(20).mean().iloc[-1] if len(h) >= 20 else h["Volume"].mean(),
                "Market Cap": mcap,
                "Float":      info.get("floatShares", None),
            })

        except Exception as e:
            print(f"[ERROR] {tkr}: {e}")
            continue

    print(f"[DONE] Fetched {len(rows)} tickers.")
    return pd.DataFrame(rows)

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
        return build_watchlist_df(self.wl)