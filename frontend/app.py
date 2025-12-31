import streamlit as st
import requests

# -----------------------------
# Helper: Render a news card
# -----------------------------
def render_card(item):
    with st.container():
        col1, col2 = st.columns([1, 3])

        with col1:
            if item.get("thumbnail"):
                st.image(item["thumbnail"], width=220)

        with col2:
            st.markdown(f"### {item['title']}")
            st.caption(f"{item['source']} • {item['published']}")
            st.write(item["summary"])
            st.markdown(f"[Read more]({item['link']})")

        st.divider()

# -----------------------------
# Config
# -----------------------------
BACKEND_URL = "http://banking-news-backend.onrender.com"

st.set_page_config(
    page_title="Banking News Dashboard",
    layout="wide"
)

st.title("🏦 Banking News Dashboard")
st.caption("Latest banking-related news from Web & YouTube")


# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Controls")
keyword = st.sidebar.text_input("Search keyword", value="banking india")
refresh = st.sidebar.button("🔄 Refresh")


# -----------------------------
# Fetch data from backend
# -----------------------------


@st.cache_data(ttl=300)
def fetch_all_news(keyword):
    try:
        response = requests.get(
            f"{BACKEND_URL}/news/all",
            params={"keyword": keyword},
            timeout=20
        )

        # If backend is not ready or errors
        if response.status_code != 200:
            st.error(f"Backend error: {response.status_code}")
            return []

        # Try parsing JSON safely
        try:
            return response.json()
        except ValueError:
            st.error("Backend returned invalid response (not JSON). Please retry.")
            return []

    except requests.exceptions.RequestException as e:
        st.error("Cannot connect to backend. It may be waking up. Please retry.")
        return []


if refresh:
    st.cache_data.clear()


# -----------------------------
# Load data
# -----------------------------
with st.spinner("Fetching latest news..."):
    data = fetch_all_news(keyword)

st.write(f"Total articles: {len(data)}")


# -----------------------------
# 🔑 DEFINE DATA BEFORE TABS
# -----------------------------
all_news = data
web_news = [item for item in data if item["source_type"] == "web"]
yt_news = [item for item in data if item["source_type"] == "youtube"]


# -----------------------------
# Tabs
# -----------------------------
tab_all, tab_web, tab_youtube = st.tabs(["All", "Web", "YouTube"])

with tab_all:
    st.subheader("All News")
    if not all_news:
        st.info("No news found.")
    for item in all_news:
        render_card(item)

with tab_web:
    st.subheader("Web News")
    if not web_news:
        st.info("No web news found.")
    for item in web_news:
        render_card(item)

with tab_youtube:
    st.subheader("YouTube News")
    if not yt_news:
        st.info("No YouTube news found.")
    for item in yt_news:
        render_card(item)
