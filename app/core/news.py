import streamlit as st
import requests
from transformers import pipeline
from datetime import datetime

@st.cache_resource
def get_sentiment_analyzer():
    return pipeline("sentiment-analysis", model="ProsusAI/finbert")

@st.cache_data(ttl=600)
def get_news(ticker, limit, alpha_api="YOUR_KEY_HERE"):
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={alpha_api}"
    r = requests.get(url)
    data = r.json()

    sentiment_analyzer = get_sentiment_analyzer()
    news = []

    feed = data.get("feed", [])[:limit]
    for article in feed:
        title = article.get("title", "No title")
        link = article.get("url", "#")
        time_published = article.get("time_published")  # Format: '20250717T190000'
        
        # Parse timestamp to readable format
        timestamp = None
        if time_published:
            try:
                dt = datetime.strptime(time_published, "%Y%m%dT%H%M%S")
                timestamp = dt.strftime("%b %d, %Y %I:%M %p")
            except:
                timestamp = "Unknown"

        sentiment = sentiment_analyzer(title)[0]

        news.append({
            "title": title,
            "url": link,
            "sentiment": sentiment["label"],
            "confidence": round(sentiment["score"], 3),
            "timestamp": timestamp
        })

    return news
