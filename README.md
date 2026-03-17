# Equity Research Agent

An automated equity research tool that generates structured one-page investment briefs from live market data and news. Enter a stock ticker and receive a professionally formatted brief with an annotated price chart, financial snapshot, 6-month price narrative, market debate framing, and analyst notes — in under 60 seconds.

Built as a demonstration of agentified investment workflows.

---

## How It Works
```
Ticker input
      ↓
data_fetcher.py     — pulls financials from yfinance, detects significant price swings
                      using a zigzag algorithm, fetches targeted news from Finnhub
                      anchored to each turning point
      ↓
brief_generator.py  — formats data into structured prompts, calls Claude API,
                      generates and saves the brief and chart
      ↓
chart_generator.py  — builds an annotated Plotly chart with peaks and troughs marked
      ↓
app.py              — Streamlit UI renders the interactive chart and brief,
                      provides markdown download
```

---

## Project Structure
```
equity-research-agent/
├── app.py                  # Streamlit web interface
├── brief_generator.py      # Prompt engineering and Claude API calls
├── data_fetcher.py         # Data pipeline — yfinance + Finnhub
├── chart_generator.py      # Plotly chart generation
├── output/                 # Generated briefs and charts saved here
├── .env                    # API keys (not committed)
├── requirements.txt        # Dependencies
└── README.md
```

---

## Setup

**1. Clone the repository and create a virtual environment:**
```bash
git clone https://github.com/kelvin-fan/equity-research-agent
cd equity-research-agent
python3 -m venv venv
source venv/bin/activate
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Configure API keys:**

Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here
```

- Anthropic API key: [console.anthropic.com](https://console.anthropic.com)
- Finnhub API key: [finnhub.io](https://finnhub.io) (free tier)

**4. Run the app:**
```bash
streamlit run app.py
```

---

## Example Output

Tested on AAPL and NVDA. Each brief includes:

- **Company Snapshot** — one-line overview with market cap and sector
- **Business Description** — revenue model and competitive position
- **Financial Snapshot** — key metrics table (P/E, margins, ROE, debt/equity)
- **Price & News Timeline** — 6-month narrative linking price moves to specific events
- **Current Market Debate** — bull vs. bear framing with the key tension identified
- **Key Risks** — 3-4 company-specific risks, not generic
- **Analyst Notes** — forward-looking catalysts and questions for the next 30-90 days

---

## Key Design Decisions

**Zigzag swing detection over daily returns**
Rather than flagging individual days with large moves, the pipeline identifies meaningful peaks and troughs using a zigzag algorithm with a 5% swing threshold. This maps to how analysts actually read charts — sustained regime changes, not daily noise.

**Turning-point-anchored news fetch**
Instead of fetching all news over 6 months, the pipeline fetches Finnhub articles in a tight ±3 day window around each turning point, sorted by proximity to the event date. This grounds the narrative in causal news rather than background noise, and keeps token usage proportional to signal.

**Two-file Claude architecture**
`data_fetcher.py` knows nothing about Claude. `brief_generator.py` knows nothing about yfinance or Finnhub. Clean separation means each file has one job and can be tested, debugged, and improved independently.

**Explicit unexplained move handling**
When no company-specific news is found around a turning point, the brief explicitly flags it as a potential macro or sector-driven move rather than inferring a plausible-sounding explanation. Intellectual honesty over narrative completeness.

---

## Dependencies

| Package | Purpose |
|---|---|
| yfinance | Price history and company financials |
| finnhub-python | Targeted company news by date range |
| anthropic | Claude API for brief generation |
| streamlit | Web interface |
| plotly | Interactive price chart |
| kaleido | Static chart export to PNG |
| python-dotenv | Environment variable management |

---

## Limitations

- News quality depends on Finnhub free tier — irrelevant articles may appear and are filtered by Claude during brief generation
- Price data and financials sourced from Yahoo Finance via yfinance — suitable for research purposes, not trading
- Coverage limited to North American equities supported by Finnhub's free tier