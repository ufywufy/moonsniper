import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
def get_polygon(ticker, timeframe, api_key):
    """
    Fetch full intraday data (pre-market, regular, post-market) from Polygon.io.
    Supports "1d" and "5d" timeframes.

    Returns DataFrame with datetime index (US/Eastern), and ["Close", "Volume"] columns.
    """
    now = datetime.now()

    if timeframe == "1d":
        start = now - timedelta(days=1)
    elif timeframe == "5d":
        start = now - timedelta(days=5)
    else:
        return pd.DataFrame()

    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{start.strftime('%Y-%m-%d')}/{now.strftime('%Y-%m-%d')}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 10000,
        "apiKey": api_key,
    }

    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json().get("results", [])
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["t"] = pd.to_datetime(df["t"], unit="ms")
        df.set_index("t", inplace=True)
        df.rename(columns={"c": "Close", "v": "Volume"}, inplace=True)

        # Convert UTC to US/Eastern for proper market-time display
        df.index = df.index.tz_localize("UTC").tz_convert("US/Eastern")

        return df[["Close", "Volume"]]

    except requests.exceptions.HTTPError as e:
        # Catch HTTP errors like 401/403/429 explicitly
        try:
            status_code = e.response.status_code
        except:
            status_code = "unknown_http"
        print(f"[Polygon Error] {e} (status {status_code})")
        return ("polygon_error", status_code)

    except requests.exceptions.RequestException as e:
        # Catch broader request exceptions
        print(f"[Polygon Error] Request failure: {e}")
        return ("polygon_error", "request_exception")

    except Exception as e:
        print(f"[Polygon Error] {e}")
        return ("polygon_error", "unknown")