import streamlit as st
import requests
from datetime import datetime

# ===============================
# CONFIG
# ===============================

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Banking News Intelligence System",
    layout="wide"
)

# ===============================
# UTILS
# ===============================


def format_date(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M")
    except:
        return "Unknown"


def safe_get(endpoint):
    try:
        r = requests.get(f"{BACKEND_URL}{endpoint}", timeout=15)
        if r.status_code == 200:
            return r.json()
        return []
    except:
        return []


def ask_chatbot(question):
    try:
        r = requests.post(
            f"{BACKEND_URL}/chat",
            params={"query": question},
            timeout=30
        )

        if r.status_code == 200:
            return r.json().get("answer", "")
        else:
            return None

    except:
        return None


# ===============================
# HEADER
# ===============================

st.title("Banking News Intelligence System")

st.markdown(
    """
AI-powered Banking News Aggregation and Analysis Platform
"""
)

st.divider()

# ===============================
# TABS
# ===============================

tab1, tab2 = st.tabs(["News Dashboard", "AI Chatbot"])


# ===============================
# TAB 1 : NEWS
# ===============================

with tab1:

    st.subheader("Latest Banking & Financial News")

    with st.spinner("Loading news..."):

        google_news = safe_get("/news/google")
        youtube_news = safe_get("/news/youtube")

        if not isinstance(google_news, list):
            google_news = []

        if not isinstance(youtube_news, list):
            youtube_news = []

        all_news = google_news + youtube_news

    if len(all_news) == 0:
        st.warning("No news available at the moment.")
        st.stop()

    for i, item in enumerate(all_news, start=1):

        col1, col2 = st.columns([1, 3])

        # ---------------- LEFT IMAGE ----------------
        with col1:

            if item.get("thumbnail"):
                st.image(
                    item["thumbnail"],
                    use_container_width=True
                )
            else:
                st.image(
                    "https://via.placeholder.com/150",
                    use_container_width=True
                )

        # ---------------- RIGHT TEXT ----------------
        with col2:

            st.markdown(f"### {i}. {item.get('title','No Title')}")

            st.write(item.get("summary", "No summary available."))

            source = item.get("source", "Unknown")
            date = format_date(item.get("published", ""))

            st.markdown(
                f"""
**Source:** {source}  
**Published:** {date}
"""
            )

            if item.get("url"):
                st.markdown(f"[Open Link]({item['url']})")

        st.divider()


# ===============================
# TAB 2 : CHATBOT
# ===============================

with tab2:

    st.subheader("AI Banking Assistant")

    st.markdown(
        """
Ask questions related to RBI regulations, banking policies,
and financial documents.
"""
    )

    # Sample Questions
    st.markdown("### Sample Questions")

    sample_questions = [
        "What are the latest RBI guidelines on digital lending?",
        "Explain recent changes in repo rate.",
        "What is the RBI policy on NPAs?",
        "Summarize latest RBI circulars.",
        "What are capital adequacy norms?"
    ]

    selected = st.selectbox(
        "Choose a sample question",
        ["Select a question"] + sample_questions
    )

    if selected != "Select a question":
        st.session_state["user_question"] = selected

    # Input box
    question = st.text_input(
        "Enter your question:",
        value=st.session_state.get("user_question", "")
    )

    ask_btn = st.button("Ask")

    if ask_btn:

        if not question.strip():
            st.warning("Please enter a valid question.")
            st.stop()

        with st.spinner("Generating answer..."):

            answer = ask_chatbot(question)

        if answer is None:
            st.error(
                "Server error. Please try again later."
            )

        else:

            st.markdown("### Answer")

            st.write(answer)

            # Citation placeholder
            st.markdown("### Sources")
            st.info(
                "Document citations and page numbers "
                "will be added in future versions."
            )
