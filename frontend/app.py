import streamlit as st
import requests


# -----------------------------
# Config
# -----------------------------
BACKEND_URL = "https://banking-news-dashboard.onrender.com"


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="Banking News Dashboard",
    layout="wide"
)

st.title("Banking News Dashboard")
st.caption("Latest banking-related news from Web & YouTube")


# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Controls")
keyword = st.sidebar.text_input("Search keyword", value="banking india")
refresh = st.sidebar.button("🔄 Refresh")


# -----------------------------
# Safe backend fetch (VERY IMPORTANT)
# -----------------------------
@st.cache_data(ttl=120)
def fetch_all_news(keyword):
    try:
        response = requests.get(
            f"{BACKEND_URL}/news/all",
            params={"keyword": keyword},
            timeout=25
        )

        if response.status_code != 200:
            st.warning("Backend is starting up. Please retry.")
            return []

        if "application/json" not in response.headers.get("content-type", ""):
            st.warning("Backend not ready yet. Please retry.")
            return []

        return response.json()

    except requests.exceptions.Timeout:
        st.warning("Backend waking up (cold start). Please retry.")
        return []

    except requests.exceptions.RequestException:
        st.warning("Cannot connect to backend. Please retry.")
        return []

    except ValueError:
        st.warning("Invalid response from backend. Please retry.")
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
# Split data
# -----------------------------
all_news = data
web_news = [item for item in data if item["source_type"] == "web"]
yt_news = [item for item in data if item["source_type"] == "youtube"]


# -----------------------------
# Card renderer
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
            st.markdown(f"🔗 [Read more]({item['link']})")

        st.divider()


# -----------------------------
# Tabs
# -----------------------------
tab_all, tab_web, tab_youtube = st.tabs(["All", "Web", "YouTube"])

with tab_all:
    for item in all_news:
        render_card(item)

with tab_web:
    for item in web_news:
        render_card(item)

with tab_youtube:
    for item in yt_news:
        render_card(item)
