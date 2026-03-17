import plotly.graph_objects as go
from datetime import datetime

def build_chart(price_history: dict, events: list) -> go.Figure:
    """
    Builds an annotated 6-month price chart with turning points marked.

    Args:
        price_history: Price history dictionary from get_price_history().
        events: List of turning point event dictionaries from get_targeted_news().

    Returns:
        A Plotly Figure object ready for rendering or export.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=price_history["dates"],
        y=price_history["closes"],
        mode="lines",
        name="Price",
        line=dict(color="#2563eb", width=2),
        hovertemplate="<b>%{x}</b><br>$%{y:.2f}<extra></extra>"
    ))

    peak_dates, peak_prices, peak_labels = [], [], []
    trough_dates, trough_prices, trough_labels = [], [], []

    for event in events:
        date = event["date"]
        price = event["price"]

        if event["has_news"]:
            label = event["articles"][0]["title"]
        else:
            label = "No company-specific news — likely macro/sector move"

        if event["type"] == "peak":
            peak_dates.append(date)
            peak_prices.append(price)
            peak_labels.append(label)
        else:
            trough_dates.append(date)
            trough_prices.append(price)
            trough_labels.append(label)

    fig.add_trace(go.Scatter(
        x=peak_dates,
        y=peak_prices,
        mode="markers",
        name="Peak",
        marker=dict(color="#dc2626", size=10, symbol="triangle-down"),
        text=peak_labels,
        hovertemplate="<b>%{x}</b><br>$%{y:.2f}<br><br>%{text}<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=trough_dates,
        y=trough_prices,
        mode="markers",
        name="Trough",
        marker=dict(color="#16a34a", size=10, symbol="triangle-up"),
        text=trough_labels,
        hovertemplate="<b>%{x}</b><br>$%{y:.2f}<br><br>%{text}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(text="6-Month Price History with Turning Points", font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
    )

    return fig


def save_chart(fig: go.Figure, ticker: str, timestamp: str) -> str:
    """
    Saves a Plotly figure as a static PNG file.

    Args:
        fig: The Plotly Figure object from build_chart().
        ticker: The stock ticker symbol, used in the filename.
        timestamp: Timestamp string used to match the brief filename.

    Returns:
        The filepath where the chart was saved.
    """
    import os
    filepath = os.path.join("output", f"{ticker}_{timestamp}_chart.png")
    fig.write_image(filepath, width=1200, height=500, scale=2)
    return filepath