# 🌒 Moon Sniper

Moon Sniper is a completely FREE, open source stock screener and alerting platform you can run locally. Powered by Python + Streamlit. Upload your own `.txt` watchlists and unlock a plethora of awesome tools most platforms hide behind subscriptions:

Demo here
[![Watch the demo](https://img.youtube.com/vi/KVk3TEjbimY/0.jpg)](https://www.youtube.com/watch?v=KVk3TEjbimY)

## 🔫 Features

- Interactive table with 12 key stat columns (Price, RSI, % Change, Avg Vol, Market Cap, Float, PE Ratio, EPS, etc.)
- Dynamic filtering, ascending/descending rows, sliders, and value selectors
- Custom filter profiles (ex: breakout, dip catcher, moon sniper, safe growth)
- Export filtered tickers as `.txt` files
- Advanced filter expressions (ex: RSI < 30 and Price > 40)
- Intraday and extended hours charts with volume bars and MACD/RSI indicators, auto-refresh every 5 min
- Sentiment-analyzed news headlines from AlphaVantage + FinBERT
- Unlimited custom alerts with filter logic via emails, webhooks, or desktop. No expiration, no limits.
- DNA codes for profiles and alerts, share and import setups with a click!

All you need is Python, then run `setup.bat` and `main.bat`

## 🚀 v0.2 Update Highlights

- 📈 Added PE Ratio, EPS, and daily % Change to stat table and filters
- 🧠 AI-powered sentiment analysis on recent news headlines per ticker
- 🖼️ Charts with indicators EMA 9, VWAP and Bollinger Bands
- ⚙️ Smarter caching and performance improvements
- 🧪 Prepping for ML-compatible CSV output and historical logs

Updated config.yaml
    + added field alpha_key
    + added field news_limit (headlines shown at a time)
Updated dna format
Updated filters/profile

## 🛠️ Getting Started

1. Install Requirements
Install Python
Run `setup.bat` which downloads all the requirements

2. Setup Config
Fill out config.yaml, you can open this as a `.txt` file
Add watchlists as `.txt` files (1 ticker per line) inside the watchlists/ folder

3. Launch Streamlit UI
Run `main.bat`
This opens your local web UI where you do everything

4. Start the Alerts Daemon (Optional)
If you don't have the UI open, you can run `alerts.bat` which will run your alerts in the background

## 🔢 Expression Syntax

Expressions are mathematical and intuitive, used by both advanced filtering and the alerts
ex: RSI > 70 and AvgVolume > 1000000
Price < 10 and MACD > 0

## 📧 Alerts

Desktop (local notifications)
Email (via Brevo)
Webhooks (like Discord)

Fully custom
Persistent
No duplicates (triggered alerts auto-remove or mark)

## 🧬 DNA (Import/Export)

Export filters/alerts into readable DNA codes
ex: `ms:filter,a_cool_name,pc<1000,rsit<60,vm<0.5,mcc:100KK,fc:1KK,MACD:true`
Share or import setups easily through the UI

## ⚠️ Disclaimer

Moon Sniper is alpha-stage software. This was built fast, ugly, but functional. Expect bugs. Expect weirdness. But it’s free forever, and it will evolve.

## 🤝 Community

Ideas? Feedback? Need help? Just wanna vibe?
Whether you're a beginner or a seasoned sniper, reach out, open an issue, or submit a pull request (please)
https://discord.gg/E6x2wFzCtX
Happy sniping.
ufywfuy

## License

MIT
