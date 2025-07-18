import pandas as pd

class WatchlistView:
    def __init__(self, watchlistdf: pd.DataFrame):
        self.field_map = {
            "Price": "Price",
            "RSI": "RSI",
            "MACD": "MACD",
            "Volume": "Volume",
            "AvgVol": "Avg Vol",
            "MarketCap": "Market Cap",
            "Float": "Float",
            "PERatio": "PE Ratio",
            "EPS": "EPS",
            "PctChange": "Pct Change"
        }
        self.df = watchlistdf.copy()
        self.df["TopPick"] = False
        self.df_pretty = None

    def apply_filters(self, price, rsi, vol, mc, float, only_macd, pe_max, eps_min, pct_min):
        cond = (
            (self.df["Price"]      <= price) &
            (self.df["RSI"]        <= rsi) &
            (self.df["Volume"]     >  vol * self.df["Avg Vol"]) &
            (self.df["Market Cap"] <= mc) &
            ((self.df["Float"].isna()) | (self.df["Float"] <= float)) &
            ((self.df["PE Ratio"].isna()) | (self.df["PE Ratio"] <= pe_max)) &
            ((self.df["EPS"].isna()) | (self.df["EPS"] >= eps_min)) &
            (self.df["Pct Change"] >= pct_min)
        )
        if only_macd:
            cond &= self.df["MACD"] > 0
        self.df["TopPick"] = cond


    def format_df(self):
        d = self.df.copy()
        d["Price"]       = d["Price"].round(2)
        d["RSI"]         = d["RSI"].round(2)
        d["MACD"]        = d["MACD"].round(4)
        d["Volume"]      = d["Volume"].round(2)
        d["Avg Vol"]     = d["Avg Vol"].round(2)
        d["Market Cap"]  = d["Market Cap"].round(2)
        d["Float"]       = d["Float"].round(2)
        d["PE Ratio"]    = d["PE Ratio"].round(2)
        d["EPS"]         = d["EPS"].round(2)
        d["Pct Change"]  = d["Pct Change"].round(2)
        self.df_pretty = d

    def search(self, searchtxt):
        if searchtxt:
            mask = self.df_pretty["Ticker"].str.contains(searchtxt, case=False)
            self.df = self.df[mask.values]
            self.df_pretty = self.df_pretty[mask]
        return (self.df, self.df_pretty)

    def expr(self, exprtxt):
        try:
            if exprtxt:
                parsed_expr = self.parse_query(exprtxt, self.field_map)
                self.df = self.df.query(parsed_expr)
                self.df_pretty = self.df_pretty[self.df_pretty["Ticker"].isin(self.df["Ticker"])]
            return (self.df, self.df_pretty)
        except Exception as e:
            return False

    def parse_query(self, query, field_map):
        import re
        expr = query
        for key, col in field_map.items():
            expr = re.sub(rf"\b{key}\b", f"`{col}`", expr)
        return expr
