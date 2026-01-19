import streamlit as st
import requests
from datetime import datetime

# ======================================================
# CONFIG
# ======================================================
BACKEND_URL = "http://127.0.0.1:8000"
USE_BACKEND = True  # set False if backend is down

st.set_page_config(
    page_title="Banking News Intelligence System",
    layout="wide"
)

# ======================================================
# HELPERS
# ======================================================
def safe_get(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def load_news():
    if USE_BACKEND:
        data = safe_get(f"{BACKEND_URL}/news/all")
        if data:
            return data

    # ---------- Fallback sample data ----------
    return [
        {
            "title": "RBI likely to maintain repo rate amid inflation watch",
            "summary": "Analysts expect the Reserve Bank of India to keep policy rates unchanged.",
            "published": "2026-01-12",
            "source": "Reuters",
            "url": "#",
            "thumbnail": None,
            "source_type": "google_news"
        },
        {
            "title": "Indian banks see rise in retail credit demand",
            "summary": "Credit growth remains strong in the retail and MSME segments.",
            "published": "2026-01-11",
            "source": "Bloomberg",
            "url": "#",
            "thumbnail": None,
            "source_type": "google_news"
        }
    ]


def ask_chatbot(query):
    try:
        r = requests.post(
            f"{BACKEND_URL}/chat",
            json={"query": query},
            timeout=30
        )
        if r.status_code == 200:
            return r.json().get("answer")
    except Exception:
        pass

    return (
        "The system is currently running in offline mode. "
        "This response is a placeholder generated for demonstration."
    )


# ======================================================
# HEADER
# ======================================================
st.title("Banking News Intelligence System")
st.caption(
    "An AI-powered system for aggregating banking news and answering "
    "financial questions using retrieval-augmented generation"
)

# ======================================================
# TABS
# ======================================================
tab_news, tab_chat = st.tabs([
    "Banking News Dashboard",
    "Banking Question Answering"
])

# ======================================================
# TAB 1 — NEWS DASHBOARD
# ======================================================
with tab_news:
    st.subheader("Latest Banking News")

    news_items = load_news()

    if not news_items:
        st.warning("No news available at the moment.")
    else:
        for item in news_items:
            with st.container():
                st.markdown(f"### {item.get('title')}")

                meta = f"{item.get('source', 'Unknown')} | {item.get('published', '')}"
                st.caption(meta)

                if item.get("thumbnail"):
                    st.image(item["thumbnail"], width=350)

                st.write(item.get("summary", ""))

                if item.get("url") and item["url"] != "#":
                    st.link_button("Read full article / watch video", item["url"])

                st.divider()

# ======================================================
# TAB 2 — CHATBOT
# ======================================================
with tab_chat:
    st.subheader("Banking Question Answering System")

    st.write(
        "Ask questions related to banking regulations, RBI guidelines, "
        "interest rates, or recent developments. "
        "Answers are generated using authoritative sources."
    )

    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])

    user_query = st.chat_input(
        "Enter your banking or finance-related question"
    )

    if user_query:
        st.session_state.chat_history.append(
            {"role": "user", "content": user_query}
        )

        with st.spinner("Generating response..."):
            answer = ask_chatbot(user_query)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": answer}
        )

        st.rerun()

    st.markdown("#### Sample Questions")
    sample_questions = [
        "What action did RBI recently take against cooperative banks?",
        "How does repo rate affect bank loans and deposits?",
        "Summarize the latest RBI press releases",
    ]

    cols = st.columns(len(sample_questions))
    for i, q in enumerate(sample_questions):
        if cols[i].button(q):
            st.session_state.chat_history.append(
                {"role": "user", "content": q}
            )
            with st.spinner("Generating response..."):
                answer = ask_chatbot(q)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer}
            )
            st.rerun()
