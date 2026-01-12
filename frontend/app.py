import streamlit as st
import time
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================
CHAT_EXPIRY_MINUTES = 15
OFFLINE_MODE = True   # set False when backend is ready

# =========================
# MOCK DATA (offline mode)
# =========================
def load_mock_news():
    return [
        {
            "title": "RBI Likely to Maintain Repo Rate",
            "summary": "The Reserve Bank of India is expected to keep interest rates unchanged while monitoring inflation trends.",
            "published": "2026-01-12",
            "source": "Bloomberg",
            "url": "#",
        },
        {
            "title": "Indian Banks Report Increase in Credit Demand",
            "summary": "Banks are seeing higher loan demand from retail consumers and small businesses.",
            "published": "2026-01-11",
            "source": "Reuters",
            "url": "#",
        },
    ]

# =========================
# SESSION STATE
# =========================
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "chat_start_time" not in st.session_state:
    st.session_state.chat_start_time = datetime.now()

# =========================
# CHAT EXPIRY
# =========================
if datetime.now() - st.session_state.chat_start_time > timedelta(minutes=CHAT_EXPIRY_MINUTES):
    st.session_state.chat_messages = []
    st.session_state.chat_start_time = datetime.now()

# =========================
# PAGE HEADER
# =========================
st.title("Banking News Intelligence System")
st.caption(
    "A system for aggregating banking news and answering financial questions using large language models and retrieval-based techniques"
)

# =========================
# TABS
# =========================
tab_news, tab_chat = st.tabs(
    ["Banking News Dashboard", "Banking Question Answering"]
)

# =========================
# TAB 1 — NEWS DASHBOARD
# =========================
with tab_news:
    st.header("Banking News Dashboard")
    st.write(
        "This section presents recent banking and financial news curated "
        "from trusted sources and summarized for quick understanding."
    )

    news_items = load_mock_news() if OFFLINE_MODE else []

    for item in news_items:
        with st.container():
            st.subheader(item["title"])
            st.caption(f'{item["source"]} | {item["published"]}')
            st.write(item["summary"])
            st.link_button("View Original Source", item["url"])
            st.divider()

# =========================
# TAB 2 — CHATBOT (RAG)
# =========================
with tab_chat:
    st.header("Banking Question Answering System")
    st.write(
        "This chatbot answers banking and financial questions using "
        "retrieval-augmented generation over authoritative documents "
        "such as RBI publications."
    )

    # Display chat history
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    # User input
    user_query = st.chat_input(
        "Enter a question related to banking, interest rates, or financial regulations"
    )

    if user_query:
        st.session_state.chat_messages.append(
            {"role": "user", "content": user_query}
        )

        with st.spinner("Generating response..."):
            time.sleep(1.5)  # simulate backend delay

            # Replace with: rag.answer(user_query)
            answer = (
                "Based on recent RBI guidelines and banking data, "
                "interest rates are expected to remain stable while "
                "the central bank continues to focus on inflation control."
            )

        st.session_state.chat_messages.append(
            {"role": "assistant", "content": answer}
        )

        st.rerun()

    st.caption(
        "Chat history is maintained temporarily and resets automatically "
        "after 15 minutes."
    )
    st.subheader("Sample Questions")

sample_questions = [
    "What is the role of RBI in controlling inflation?",
    "How do repo rate changes affect bank loans and deposits?",
    "What are the recent trends in banking sector credit growth?"
]

cols = st.columns(len(sample_questions))

for i, question in enumerate(sample_questions):
    if cols[i].button(question):
        st.session_state.chat_messages.append(
            {"role": "user", "content": question}
        )

        with st.spinner("Generating response..."):
            time.sleep(1.5)  # simulate backend delay

            # Replace with rag.answer(question) later
            answer = (
                "The Reserve Bank of India controls inflation mainly through "
                "monetary policy tools such as repo rate adjustments, which "
                "influence borrowing costs and liquidity in the banking system."
            )

        st.session_state.chat_messages.append(
            {"role": "assistant", "content": answer}
        )

        st.rerun()
