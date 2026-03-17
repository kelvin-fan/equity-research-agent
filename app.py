import streamlit as st
from brief_generator import generate_brief, save_brief

st.set_page_config(
    page_title="Equity Research Agent",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Equity Research Agent")
st.markdown(
    "Generates a structured one-page investment brief from live market data and news. "
    "Powered by yfinance, Finnhub, and Claude."
)
st.divider()

if "brief" not in st.session_state:
    st.session_state.brief = None
    st.session_state.fig = None
    st.session_state.filepath = None

col1, col2 = st.columns([1, 4])

with col1:
    ticker_input = st.text_input(
        "Ticker Symbol",
        placeholder="e.g. AAPL, NVDA, TSLA",
        max_chars=10
    ).upper().strip()

with col2:
    st.write("")
    st.write("")
    generate_button = st.button("Generate Brief", type="primary")

if generate_button and ticker_input:
    with st.spinner(f"Researching {ticker_input}..."):
        try:
            brief, fig, timestamp = generate_brief(ticker_input)
            filepath = save_brief(ticker_input, brief, timestamp)
            st.session_state.brief = brief
            st.session_state.fig = fig
            st.session_state.filepath = filepath
        except ValueError as e:
            st.error(f"Error: {e}")

elif generate_button and not ticker_input:
    st.warning("Please enter a ticker symbol.")

if st.session_state.brief:
    st.plotly_chart(st.session_state.fig, use_container_width=True)
    
    st.divider()
    
    st.markdown(st.session_state.brief)
    
    st.divider()
    
    with open(st.session_state.filepath, "r") as f:
        st.download_button(
            label="Download Brief (.md)",
            data=f.read(),
            file_name=st.session_state.filepath.split("/")[-1],
            mime="text/markdown"
        )
