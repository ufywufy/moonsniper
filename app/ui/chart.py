import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from ui.polygon import get_polygon
import pandas as pd
import pytz
from datetime import datetime, time
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands

def calculate_vwap(df):
    pv = (df["Close"] * df["Volume"])
    cum_pv = pv.cumsum()
    cum_vol = df["Volume"].cumsum()
    return cum_pv / cum_vol

def is_market_open():
    now = datetime.now(pytz.timezone("US/Eastern"))
    return now.weekday() < 5 and time(9, 30) <= now.time() <= time(16, 0)

@st.cache_data(ttl=60 if is_market_open() else 3600)
def get_histogram(ticker, timeframe):
    tk = yf.Ticker(ticker)
    if timeframe == "1d":
        return tk.history(period="1d", interval="1m")
    elif timeframe == "5d":
        return tk.history(period="5d", interval="15m")
    elif timeframe == "All":
        return tk.history(period="max")
    else:
        return tk.history(period=timeframe.lower())


class Chart:
    def __init__(self, selected, timeframe, intraday=True, pgk=None, indicators=None):
        self.tk = selected
        self.tf = timeframe
        self.intraday = intraday
        self.pgk = pgk
        self.indicators = indicators or {}

    def histogram(self):
        if self.tf in ("1d", "5d") and not self.intraday and self.pgk:
            result = get_polygon(self.tk, self.tf, self.pgk)
            if isinstance(result, tuple) and result[0] == "polygon_error":
                return result
            if result is None or result.empty:
                return ("polygon_error", "empty")
            return result

        return get_histogram(self.tk, self.tf)

    def figure(self):
        hist = self.histogram()
        if isinstance(hist, tuple) and hist[0] == "polygon_error":
            return hist

        hist = hist.copy()
        hist.dropna(inplace=True)

        # indicators
        if self.indicators.get("ema9"):
            hist["EMA_9"] = EMAIndicator(close=hist["Close"], window=9).ema_indicator()

        if self.indicators.get("vwap") and "Close" in hist and "Volume" in hist:
            hist["VWAP"] = calculate_vwap(hist)

        if self.indicators.get("bbands") and "Close" in hist:
            bb = BollingerBands(close=hist["Close"], window=20, window_dev=2)
            hist["bb_upper"] = bb.bollinger_hband()
            hist["bb_lower"] = bb.bollinger_lband()

        sp, ep = hist["Close"].iloc[[0, -1]]
        clr = "green" if ep >= sp else "red"

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["Close"], mode="lines", name="Price",
            line=dict(color=clr, width=2)
        ))

        # overlays
        if self.indicators.get("ema9") and "EMA_9" in hist:
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist["EMA_9"], name="EMA 9",
                line=dict(color="orange", width=1.5, dash="dot")
            ))

        if self.indicators.get("vwap") and "VWAP" in hist:
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist["VWAP"], name="VWAP",
                line=dict(color="purple", width=1.5)
            ))

        if self.indicators.get("bbands") and "bb_lower" in hist and "bb_upper" in hist:
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist["bb_lower"], name="BB Lower",
                line=dict(color="blue", width=1, dash="dot")
            ))
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist["bb_upper"], name="BB Upper",
                line=dict(color="blue", width=1, dash="dot")
            ))

        fig.add_trace(go.Bar(
            x=hist.index, y=hist["Volume"], yaxis="y2", opacity=0.3, name="Volume", marker=dict(color="rgba(0, 123, 255, 0.5)")
        ))

        fig.update_layout(
            yaxis=dict(title="Price"),
            yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False),
            margin=dict(l=40, r=40, t=30, b=20),
        )

        # time axis formatting
        if self.tf in ("1d", "5d"):
            fig.update_xaxes(
                tickformat="%b %d\n%H:%M",
                range=[hist.index.min(), hist.index.max()],
                rangebreaks=[dict(bounds=["sat", "mon"])]
            )

            if not self.intraday:
                hist_dates = pd.to_datetime(hist.index.date).unique()
                for d in hist_dates:
                    start = pd.Timestamp(d, tz="US/Eastern") + pd.Timedelta(hours=16)
                    end = pd.Timestamp(d, tz="US/Eastern") + pd.Timedelta(hours=20)
                    fig.add_vrect(x0=start, x1=end, fillcolor="purple", opacity=0.1, layer="below", line_width=0)
        else:
            fig.update_xaxes(range=[hist.index.min(), hist.index.max()])

        return fig
