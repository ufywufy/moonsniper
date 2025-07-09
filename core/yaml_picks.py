import pandas as pd

class YamlPicks:
    def __init__(self, filters, df):
        self.filters = filters
        self.df = df

    def get(self):
        # pull original filter values from config.yaml
        orig_price   = float(self.filters["price_ceiling"])
        orig_rsi     = int(self.filters["rsi_threshold"])
        orig_vol_mul = float(self.filters["volume_multiplier"])
        orig_mc      = float(self.filters["market_cap_ceiling"])
        orig_float   = float(self.filters.get("float_ceiling", 0))
        orig_macd    = self.filters.get("only_positive_macd", False)

        # apply YAML based filters to the df
        df_picks = self.df[
            (self.df["Price"]      <= orig_price) &
            (self.df["RSI"]        <= orig_rsi) &
            (self.df["Volume"]     >  orig_vol_mul * self.df["Avg Vol"]) &
            (self.df["Market Cap"] <= orig_mc) &
            ((self.df["Float"].isna()) | (self.df["Float"] <= orig_float))
        ]

        if orig_macd:
            df_picks = df_picks[df_picks["MACD"] > 0]

        result = {}
        for _, row in df_picks.iterrows():
            reasons = []
            if row["Price"] <= orig_price:
                reasons.append(f"Price {row["Price"]:.2f}≤{orig_price}")
            if row["RSI"] <= orig_rsi:
                reasons.append(f"RSI {row["RSI"]:.1f}≤{orig_rsi}")
            if row["Volume"] > orig_vol_mul * row["Avg Vol"]:
                reasons.append("Vol spike")
            if row["Market Cap"] <= orig_mc:
                reasons.append(f"MCap≤{orig_mc:,}")
            if pd.notna(row["Float"]) and row["Float"] <= orig_float:
                reasons.append(f"Float≤{orig_float:,}")
            if orig_macd and row["MACD"] > 0:
                reasons.append("MACD+")

            result[row["Ticker"]] = "; ".join(reasons)

        return result