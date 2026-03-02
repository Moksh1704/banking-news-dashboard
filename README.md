# Banking News Dashboard

A web-based banking and financial news aggregation dashboard that collects curated news from trusted online sources and YouTube channels and presents them through a unified interface.

This project is an early functional module of a larger **Banking News Intelligence System**, which will eventually integrate Retrieval-Augmented Generation (RAG) and domain-specific financial knowledge retrieval.

---

## Overview

The **Banking News Dashboard** aggregates banking and financial sector updates from multiple authoritative sources and displays them in a structured dashboard.

It combines RSS feeds, curated YouTube financial channels, and preliminary RBI document scraping to provide consolidated domain-specific insights.

The current version focuses on:

- Reliable data ingestion  
- Structured news processing  
- Modular backend services  
- Dashboard visualization  

Future versions will integrate semantic search and RAG-based financial question answering.

---

## Features

- Google News RSS aggregation for banking/finance topics  
- Financial news retrieval from trusted YouTube channels  
- Data filtering and structuring pipeline  
- FastAPI-based modular backend APIs  
- Streamlit interactive dashboard frontend  
- RBI website scraping module (partial implementation)  
- Experimental vector store prototype  
- Early RAG pipeline scaffolding  
- Service-oriented backend architecture  

---

## Architecture

The system follows a modular data-pipeline architecture:


News Sources

├── Google News RSS

├── YouTube Channels

└── RBI Website (partial)

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


Experimental components (vector store and RAG) are present but not yet integrated into the production pipeline.

---

## Tech Stack

### Backend
- Python  
- FastAPI  
- Requests  
- Feedparser  
- BeautifulSoup  

### Frontend
- Streamlit  

### Data Processing
- Pandas  
- NumPy  

### AI / Experimental Modules
- Sentence Transformers  
- Google Gemini API (testing stage)  
- Vector store prototype  
- RAG pipeline scaffolding  

---

## Project Structure


backend/

app/

main.py

services/

google_news_rss.py

youtube_news.py

rbi_scraper.py

vector_store.py

rag_pipeline.py

frontend/

app.py

tests/

requirements.txt

render.yaml

runtime.txt


---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/Moksh1704/banking-news-dashboard.git
cd banking-news-dashboard
```

2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate      # Windows
```
3. Install Dependencies
```bash
pip install -r requirements.txt
```

#Running Backend

Start the FastAPI backend server:
```bash
cd backend/app
uvicorn main:app --reload
```

Backend will run at:

```bash
http://127.0.0.1:8000
```

API docs available at:
```bash
http://127.0.0.1:8000/docs
```

##Running Frontend

Launch the Streamlit dashboard:
```bash
cd frontend
streamlit run app.py
```
Dashboard will open in browser at:
```bash
http://localhost:8501
```

---

### Example Capabilities

Current system can:
- Fetch latest banking news from Google News RSS
- Retrieve financial videos from curated YouTube sources
- Filter and structure domain-specific news
- Display aggregated insights in a dashboard
- Serve news via backend APIs
- Provide foundation for RBI document ingestion

---

### Future Enhancements

Planned extensions toward the full Banking News Intelligence System:
- RBI document corpus ingestion and indexing
- Semantic search over financial documents
- Vector database integration
- Retrieval-Augmented Generation (RAG) chatbot
- Financial topic classification
- News summarization using LLMs
- Relevance ranking and personalization
- Source credibility scoring
- Automated financial alerts
