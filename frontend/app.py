import streamlit as st
import requests
from datetime import datetime

# ========================
# CONFIG
# ========================
BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Banking News Dashboard",
    page_icon="",
    layout="wide"
)

# ========================
# SIDEBAR — CHATBOT
# ========================
with st.sidebar:
    st.markdown("##  Banking Assistant")
    st.caption("AI-powered banking intelligence")

    st.write(
        "Ask questions based **only on the banking news and regulatory data "
        "collected by this system**."
    )

    st.divider()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input(
        "Example: What are recent RBI compliance issues?"
    )

    if user_query:
        # User message
        st.session_state.chat_history.append(
            {"role": "user", "content": user_query}
        )

        with st.chat_message("assistant"):
            with st.spinner("Analyzing banking data..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/ask",
                        json={"question": user_query},
                        timeout=60
                    )

                    if response.status_code == 200:
                        answer = response.json().get("answer", "")
                    else:
                        answer = "Unable to retrieve response."

                except Exception:
                    answer = "Backend service is not reachable."

                st.markdown(answer)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": answer}
        )

# ========================
# HEADER
# ========================
st.markdown(
    """
    <h1 style="margin-bottom:0;"> Banking News Dashboard</h1>
    <p style="color:gray; margin-top:4px;">
    Latest curated banking-related news from trusted sources
    </p>
    """,
    unsafe_allow_html=True
)

st.divider()

# ========================
# NEWS FEED — REAL DATA
# ========================
st.subheader("Latest Banking News")

with st.spinner("Fetching latest banking news..."):
    try:
        response = requests.get(
            f"{BACKEND_URL}/news/google",
            params={"limit": 15},
            timeout=15
        )
        news_articles = response.json()
    except Exception:
        news_articles = []

# Debug line (you can remove later)
st.caption(f"Articles received from backend: {len(news_articles)}")

if not news_articles:
    st.warning("No news articles available at the moment.")
else:
    for article in news_articles:
        with st.container(border=True):
            st.markdown(f"### {article['title']}")
            st.caption(f"{article['source']} • {article['published']}")
            st.write(article["summary"])

            if article.get("url"):
                st.markdown(f"[Read full article]({article['url']})")

# ========================
# FOOTER
# ========================
st.divider()
st.caption(
    f"© {datetime.now().year} Banking News Dashboard "
)
