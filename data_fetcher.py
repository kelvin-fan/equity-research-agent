import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import yfinance as yf
import finnhub
try:
    import streamlit as st
    FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]
except Exception:
    load_dotenv()
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)


def validate_ticker(ticker: str) -> bool:
    """
    Checks whether a given ticker symbol is valid.

    Args:
        ticker: The stock ticker symbol to validate.

    Returns:
        True if the ticker exists, False otherwise.
    """
    stock = yf.Ticker(ticker)
    info = stock.info
    return "symbol" in info


def get_financials(ticker: str) -> dict:
    """
    Fetches key financial metrics for a given stock ticker.

    Args:
        ticker: The stock ticker symbol (e.g. 'AAPL', 'NVDA').

    Returns:
        A dictionary containing key financial metrics and company info.
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    financials = {
        "company_name": info.get("longName", "N/A"),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "market_cap": info.get("marketCap", "N/A"),
        "pe_ratio": info.get("trailingPE", "N/A"),
        "revenue": info.get("totalRevenue", "N/A"),
        "profit_margin": info.get("profitMargins", "N/A"),
        "debt_to_equity": info.get("debtToEquity", "N/A"),
        "return_on_equity": info.get("returnOnEquity", "N/A"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow", "N/A"),
        "business_summary": info.get("longBusinessSummary", "N/A"),
    }

    return financials


def get_price_history(ticker: str, swing_threshold: float = 5.0) -> dict:
    """
    Fetches 6 months of daily price history and detects significant price swings
    using a zigzag algorithm to identify meaningful peaks and troughs.

    Args:
        ticker: The stock ticker symbol (e.g. 'AAPL', 'NVDA').
        swing_threshold: Minimum percentage move to qualify as a significant swing.
                        Defaults to 5.0%.

    Returns:
        A dictionary containing dates, closing prices, summary stats,
        and a list of significant swings with start/end dates and magnitudes.
    """
    stock = yf.Ticker(ticker)
    history = stock.history(period="6mo")

    dates = [date.strftime("%Y-%m-%d") for date in history.index]
    closes = [round(price, 2) for price in history["Close"].tolist()]

    # --- Zigzag Detection ---
    extreme_price = closes[0]
    extreme_date = dates[0]
    direction = None
    swings = []

    for i in range(1, len(closes)):
        change = ((closes[i] - extreme_price) / extreme_price) * 100

        if direction is None:
            if change >= swing_threshold:
                direction = "up"
                swings.append({
                    "type": "trough",
                    "date": extreme_date,
                    "price": extreme_price
                })
                extreme_price = closes[i]
                extreme_date = dates[i]
            elif change <= -swing_threshold:
                direction = "down"
                swings.append({
                    "type": "peak",
                    "date": extreme_date,
                    "price": extreme_price
                })
                extreme_price = closes[i]
                extreme_date = dates[i]

        elif direction == "up":
            if closes[i] >= extreme_price:
                extreme_price = closes[i]
                extreme_date = dates[i]
            elif change <= -swing_threshold:
                direction = "down"
                swings.append({
                    "type": "peak",
                    "date": extreme_date,
                    "price": extreme_price
                })
                extreme_price = closes[i]
                extreme_date = dates[i]

        elif direction == "down":
            if closes[i] <= extreme_price:
                extreme_price = closes[i]
                extreme_date = dates[i]
            elif change >= swing_threshold:
                direction = "up"
                swings.append({
                    "type": "trough",
                    "date": extreme_date,
                    "price": extreme_price
                })
                extreme_price = closes[i]
                extreme_date = dates[i]

    # Add the final extreme as a closing point
    swings.append({
        "type": "peak" if direction == "up" else "trough",
        "date": extreme_date,
        "price": extreme_price
    })

    # --- Build swing events from consecutive peak/trough pairs ---
    significant_moves = []
    for i in range(len(swings) - 1):
        start = swings[i]
        end = swings[i + 1]
        price_change_pct = round(((end["price"] - start["price"]) / start["price"]) * 100, 2)
        significant_moves.append({
            "start_date": start["date"],
            "end_date": end["date"],
            "start_price": start["price"],
            "end_price": end["price"],
            "price_change_pct": price_change_pct,
            "direction": "up" if price_change_pct > 0 else "down"
        })

    return {
        "dates": dates,
        "closes": closes,
        "high_6mo": round(max(closes), 2),
        "low_6mo": round(min(closes), 2),
        "start_price": closes[0],
        "end_price": closes[-1],
        "price_change_pct": round(((closes[-1] - closes[0]) / closes[0]) * 100, 2),
        "significant_moves": significant_moves,
        "turning_points": swings        # ← add this line
    }


def get_news_for_date(ticker: str, start_date: str, end_date: str, target_date: str) -> list:
    """
    Fetches news articles within a date range, prioritised by proximity to a target date.

    Args:
        ticker: The stock ticker symbol (e.g. 'AAPL', 'NVDA').
        start_date: Start of date range in YYYY-MM-DD format.
        end_date: End of date range in YYYY-MM-DD format.
        target_date: The turning point date to sort proximity around.

    Returns:
        A list of up to 20 article dictionaries closest to the target date.
    """
    articles = finnhub_client.company_news(ticker, _from=start_date, to=end_date)

    news = []
    for article in articles:
        news.append({
            "title": article.get("headline", "N/A"),
            "summary": article.get("summary", "N/A"),
            "published_at": article.get("datetime", "N/A"),
            "source": article.get("source", "N/A")
        })

    target_ts = datetime.strptime(target_date, "%Y-%m-%d").timestamp()
    news.sort(key=lambda x: abs(x["published_at"] - target_ts))

    return news[:20]


def get_targeted_news(ticker: str, turning_points: list) -> list:
    """
    Fetches news articles within a tight window around each turning point.

    Args:
        ticker: The stock ticker symbol (e.g. 'AAPL', 'NVDA').
        turning_points: List of peak/trough dictionaries from get_price_history().

    Returns:
        A list of event dictionaries, each containing the turning point data
        and associated articles fetched within a ±3 day window.
    """
    events = []
    for point in turning_points:
        target = datetime.strptime(point["date"], "%Y-%m-%d")
        start_date = (target - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = (target + timedelta(days=3)).strftime("%Y-%m-%d")

        articles = get_news_for_date(ticker, start_date, end_date, point["date"])

        events.append({
            "date": point["date"],
            "price": point["price"],
            "type": point["type"],
            "articles": articles,
            "has_news": len(articles) > 0
        })

    return events


def get_company_data(ticker: str) -> dict:
    """
    Master function that fetches all data for a given ticker.
    This is the only function intended to be called externally.

    Args:
        ticker: The stock ticker symbol (e.g. 'AAPL', 'NVDA').

    Returns:
        A dictionary containing financials, price history, and targeted news events,
        or raises a ValueError if the ticker is invalid.
    """
    ticker = ticker.upper().strip()

    if not validate_ticker(ticker):
        raise ValueError(f"Invalid ticker symbol: {ticker}")

    financials = get_financials(ticker)
    price_history = get_price_history(ticker)
    events = get_targeted_news(ticker, price_history["turning_points"])

    return {
        "ticker": ticker,
        "financials": financials,
        "price_history": price_history,
        "events": events
    }