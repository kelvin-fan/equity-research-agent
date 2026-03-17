import os
import anthropic
from dotenv import load_dotenv
from datetime import datetime
from data_fetcher import get_company_data
from chart_generator import build_chart, save_chart

try:
    import streamlit as st
    ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    load_dotenv()
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def format_financials(financials: dict) -> str:
    """
    Formats the financials dictionary into a clean string for the Claude prompt.

    Args:
        financials: Dictionary of financial metrics from get_financials().

    Returns:
        A formatted string representation of key financial metrics.
    """
    def fmt(value, prefix="", suffix="", divisor=1):
        if value == "N/A":
            return "N/A"
        return f"{prefix}{value / divisor:,.2f}{suffix}"

    return f"""
Company: {financials['company_name']} | Sector: {financials['sector']} | Industry: {financials['industry']}

Financials:
- Market Cap:      {fmt(financials['market_cap'], prefix="$", divisor=1_000_000_000)} B
- Revenue:         {fmt(financials['revenue'], prefix="$", divisor=1_000_000_000)} B
- Profit Margin:   {fmt(financials['profit_margin'], suffix="%", divisor=0.01)}
- P/E Ratio:       {fmt(financials['pe_ratio'])}
- Debt/Equity:     {fmt(financials['debt_to_equity'])}
- ROE:             {fmt(financials['return_on_equity'], suffix="%", divisor=0.01)}
- 52W High:        {fmt(financials['fifty_two_week_high'], prefix="$")}
- 52W Low:         {fmt(financials['fifty_two_week_low'], prefix="$")}

Business Summary:
{financials['business_summary']}
""".strip()


def format_events(events: list) -> str:
    """
    Formats turning point events with associated news for the brief generation prompt.

    Args:
        events: List of event dictionaries from get_targeted_news().

    Returns:
        A formatted string of turning points with price context and associated articles.
    """
    lines = []
    for event in events:
        header = f"""TURNING POINT: {event['date']} | Type: {event['type'].upper()} | Price: ${event['price']}"""

        if event['has_news']:
            articles = []
            for article in event['articles']:
                date = datetime.fromtimestamp(article["published_at"]).strftime("%Y-%m-%d")
                articles.append(f"""  [{date}] {article['title']}
  Source: {article['source']}
  Summary: {article['summary']}""")
            news_block = "\n\n".join(articles)
        else:
            news_block = "  No company-specific news identified — likely macro or sector-driven move."

        lines.append(f"{header}\n\n{news_block}")

    return f"\n\n{'='*60}\n\n".join(lines)


def generate_brief(ticker: str) -> tuple:
    """
    Master function that orchestrates data fetching, chart generation,
    and brief generation. Returns the brief, chart figure, and timestamp.

    Args:
        ticker: The stock ticker symbol (e.g. 'AAPL', 'NVDA').

    Returns:
        A tuple of (markdown brief string, Plotly figure, timestamp string).
    """
    timestamp = datetime.today().strftime("%Y%m%d_%H%M%S")
    os.makedirs("output", exist_ok=True)

    print(f"Fetching data for {ticker}...")
    data = get_company_data(ticker)

    financials_str = format_financials(data["financials"])
    events_str = format_events(data["events"])

    print(f"Generating chart...")
    fig = build_chart(data["price_history"], data["events"])
    chart_path = save_chart(fig, ticker, timestamp)

    print("Generating brief...")
    price = data["price_history"]
    price_summary = f"""6-Month Price Performance:
        - Start Price: ${price['start_price']}
        - End Price:   ${price['end_price']}
        - Change:      {price['price_change_pct']}%
        - 6M High:     ${price['high_6mo']}
        - 6M Low:      ${price['low_6mo']}
    """

    prompt = f"""You are a senior equity research analyst writing a one-page investment brief.

        Your brief must follow this exact structure:

        # [Company Name] ([TICKER]) — Investment Brief
        *Generated: [today's date]*

        ## 1. Company Snapshot
        One sentence: name, sector, market cap, what they do.

        ## 2. Business Description
        3-4 sentences. What does this company actually do, how does it make money, and what is its competitive position.

        ## 3. Financial Snapshot
        Present key metrics in a clean markdown table.

        ## 4. Price & News Timeline
        Tell the story of this stock over the past 6 months using the turning points provided.
        For each turning point, explain what drove the move — link specific news events to price action.
        For turning points marked as macro/sector driven, acknowledge the move and provide context.
        Be specific — use dates, prices, and percentage moves. This should read as a coherent narrative.

        ## 5. Current Market Debate
        What are bulls arguing? What are bears arguing? What is the market currently focused on?
        Frame this as the key tension that will determine the stock's direction.

        ## 6. Key Risks
        3-4 specific, concrete risks. Not generic — tied to this company's actual situation.

        ## 7. Analyst Notes
        What does an analyst need to investigate further before forming a view?
        What data points, events, or conversations matter most in the next 30-90 days?

        ---

        Here is the data:

        FINANCIALS:
        {financials_str}

        PRICE HISTORY:
        {price_summary}

        TURNING POINT EVENTS WITH NEWS:
        {events_str}

        ---

        Important instructions:
        - Each turning point represents a meaningful peak or trough in the price chart
        - For each turning point, reason about what the news tells us about why price moved
        - Ignore any news articles that are clearly not about {ticker}
        - If the no news articles for a turning point are clearly related to {ticker} or its stock price, 
        explicitly state "No clear catalyst identified in available news" rather than inferring an explanation
        - Be specific and analytical — avoid generic statements
        - Use exact figures from the data provided
        - The brief should be dense with insight, not padding
        - Today's date is {datetime.today().strftime("%B %d, %Y")}
        - Do not use $ signs for dollar amounts — write "USD" or 
        spell out "dollars" instead, e.g. "600B USD" not "$600B"
    """

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text, fig, timestamp


def save_brief(ticker: str, brief: str, timestamp: str) -> str:
    """
    Saves the generated brief to the output folder as a markdown file.

    Args:
        ticker: The stock ticker symbol, used in the filename.
        brief: The markdown string returned by generate_brief().
        timestamp: Timestamp string from generate_brief(), shared with chart filename.

    Returns:
        The file path where the brief was saved.
    """
    filename = f"{ticker}_{timestamp}.md"
    filepath = os.path.join("output", filename)

    with open(filepath, "w") as f:
        f.write(brief)

    return filepath