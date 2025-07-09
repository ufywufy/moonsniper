import yfinance as yf

def fetch_batch_history(tickers: list[str], period="3mo", interval="1d"):
    """Use yf.download to get batch historical data"""
    return yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        group_by="ticker",
        threads=True,
        auto_adjust=True,
        progress=False,
    )
