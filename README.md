# Banking News Dashboard

A web-based banking and financial news aggregation dashboard that collects curated news from trusted online sources and YouTube channels and presents them through a unified interface.

This project is an early functional module of a larger **Banking News Intelligence System**, which will eventually integrate Retrieval-Augmented Generation (RAG) and domain-specific financial knowledge retrieval.

---

# Overview

The **Banking News Dashboard** aggregates banking and financial sector updates from multiple authoritative sources and displays them in a structured dashboard.

It combines RSS feeds, curated YouTube financial channels, and preliminary RBI document scraping to provide consolidated domain-specific insights.

The current version focuses on:

- Reliable data ingestion
- Structured news processing
- Modular backend services
- Dashboard visualization

Future versions will integrate semantic search and RAG-based financial question answering.

---

# Features

- Google News RSS aggregation for banking and finance topics
- Financial news retrieval from trusted YouTube channels
- Data filtering and structuring pipeline
- FastAPI-based modular backend APIs
- Streamlit interactive dashboard frontend
- RBI website scraping module (partial implementation)
- Experimental vector store prototype
- Early RAG pipeline scaffolding
- Service-oriented backend architecture

---

# Architecture

The system follows a modular data-pipeline architecture:

```text
News Sources
├── Google News RSS
├── YouTube Channels
└── RBI Website (Partial)

        │
        ▼

Data Ingestion Services
        │
        ▼

Filtering & Structuring Layer
        │
        ▼

Backend APIs (FastAPI)
        │
        ▼

Dashboard UI (Streamlit)
```

Experimental components such as vector stores and RAG modules are currently under development and not yet integrated into the production pipeline.

---

# Tech Stack

## Backend
- Python
- FastAPI
- Requests
- Feedparser
- BeautifulSoup

## Frontend
- Streamlit

## Data Processing
- Pandas
- NumPy

## AI / Experimental Modules
- Sentence Transformers
- Google Gemini API (Testing Phase)
- Vector Store Prototype
- RAG Pipeline Scaffolding

---

# Project Structure

```bash
banking-news-dashboard/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── services/
│   │       ├── google_news_rss.py
│   │       ├── youtube_news.py
│   │       ├── rbi_scraper.py
│   │       ├── vector_store.py
│   │       └── rag_pipeline.py
│
├── frontend/
│   └── app.py
│
├── tests/
│
├── requirements.txt
├── render.yaml
└── runtime.txt
```

---

# Installation

## 1. Clone the Repository

```bash
git clone https://github.com/Moksh1704/banking-news-dashboard.git
cd banking-news-dashboard
```

---

## 2. Create Virtual Environment

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Running the Backend

Start the FastAPI backend server:

```bash
cd backend/app
uvicorn main:app --reload
```

Backend will run at:

```bash
http://127.0.0.1:8000
```

API documentation available at:

```bash
http://127.0.0.1:8000/docs
```

---

# Running the Frontend

Launch the Streamlit dashboard:

```bash
cd frontend
streamlit run app.py
```

Dashboard will open in the browser at:

```bash
http://localhost:8501
```

---

# Example Capabilities

The current system can:

- Fetch latest banking and finance news from Google News RSS
- Retrieve financial videos from curated YouTube channels
- Filter and structure domain-specific news
- Display aggregated insights in an interactive dashboard
- Serve processed news through backend APIs
- Provide a foundation for RBI document ingestion and analysis

---

# Future Enhancements

Planned extensions toward the complete **Banking News Intelligence System** include:

- RBI document corpus ingestion and indexing
- Semantic search over financial documents
- Vector database integration
- Retrieval-Augmented Generation (RAG) chatbot
- Financial topic classification
- News summarization using LLMs
- Relevance ranking and personalization
- Source credibility scoring
- Automated financial alerts
- Real-time analytics dashboard

---

# Challenges Solved

- Aggregating multi-source financial news
- Structuring RSS feed data pipelines
- Integrating YouTube-based financial content
- Designing modular FastAPI backend services
- Building scalable ingestion architecture
- Creating a dashboard visualization pipeline
- Experimenting with vector stores and RAG workflows

---

# Use Cases

- Banking sector news monitoring
- Financial research workflows
- RBI and regulatory update tracking
- Financial intelligence systems
- AI-powered finance assistants
- Investment and market analysis dashboards

---

# Author

Developed as part of an experimental Banking News Intelligence System using FastAPI, Streamlit, and AI-assisted retrieval technologies.

---

# License

This project is intended for educational, research, and learning purposes.
