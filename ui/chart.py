import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from ui.polygon import get_polygon
import pandas as pd
import pytz
from datetime import datetime, time
import streamlit as st

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
    def __init__(self, selected, timeframe, intraday=True, pgk=None):
        self.tk = selected
        self.tf = timeframe
        self.intraday = intraday
        self.pgk = pgk

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
            return hist  # Forward the error
        sp, ep = hist["Close"].iloc[[0, -1]]
        clr = "green" if ep >= sp else "red"

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist.Close, mode="lines", name="Price",
            line=dict(color=clr, width=2)
        ))
        fig.add_trace(go.Bar(
            x=hist.index, y=hist.Volume, yaxis="y2", opacity=0.3, name="Volume"
        ))
        fig.update_layout(
            yaxis=dict(title="Price"),
            yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False),
            margin=dict(l=40, r=40, t=30, b=20),
        )

        if self.tf in ("1d", "5d"):
            fig.update_xaxes(
                tickformat="%b %d\n%H:%M",  # e.g. Jul 01\n09:00
                range=[hist.index.min(), hist.index.max()],
                rangebreaks=[
                    dict(bounds=["sat", "mon"])
                    #dict(bounds=[16, 9], pattern="hour"),
                ],
            )
            hist_dates = pd.to_datetime(hist.index.date).unique()

            if self.intraday == False:
                for d in hist_dates:
                    start = pd.Timestamp(d, tz="US/Eastern") + pd.Timedelta(hours=16)  # 4 PM
                    end   = pd.Timestamp(d, tz="US/Eastern") + pd.Timedelta(hours=20)  # 8 PM

                    fig.add_vrect(
                        x0=start, x1=end,
                        fillcolor="purple",
                        opacity=0.1,
                        layer="below",
                        line_width=0,
                    )
        else:
            fig.update_xaxes(range=[hist.index.min(), hist.index.max()])

        return fig
