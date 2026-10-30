# Banking News Intelligence System

AI-powered Banking News Aggregation and Analysis Platform. This project combines an RBI document search and question-answering backend with a Streamlit dashboard for banking news.

## Problem statement

Banking regulations and current events are published across multiple sources. This project provides a small local application to browse banking news and ask natural-language questions against an indexed set of RBI documents.

## Features

- Ingests RBI PDFs, extracts and chunks their text, and stores document metadata.
- Builds and searches a FAISS vector index using sentence-transformer embeddings.
- Answers questions over retrieved RBI passages with a Groq-hosted language model (RAG).
- Applies a narrow institution-scope filter to explicit Commercial Banks questions.
- Aggregates banking-related Google News RSS articles and recent YouTube videos in the dashboard.
- Provides a FastAPI backend and a Streamlit frontend.

> Google News and YouTube are separate news aggregation feeds. They are **not currently connected to the chatbot's RAG context**.

## Architecture

```text
RBI PDFs ──> PDF extraction/chunking ──> sentence embeddings ──> FAISS + metadata
                                                                  │
Question ──> FastAPI /chat ──> scoped retrieval ──> Groq LLM <────┘
                     │
                     └──> answer and source metadata

Google News RSS ──┐
                  ├──> FastAPI news routes ──> Streamlit News Dashboard
YouTube Data API ─┘
```

The RBI index is loaded by the backend from `backend/app/data/rbi.index` and its paired `rbi_docs.json` metadata file. If an index is missing, the RAG pipeline can attempt to build one from RBI sources; that process requires network access.

## Technology stack

- **Python 3.11**
- **FastAPI** and **Uvicorn** — API backend
- **Streamlit** — web dashboard and chat UI
- **FAISS** — vector similarity search
- **Sentence Transformers** — text embeddings (`all-MiniLM-L6-v2`)
- **Groq** — language-model response generation
- **PyMuPDF** and **pypdf** — PDF processing
- **feedparser**, **Requests**, and **BeautifulSoup** — news collection and parsing
- **NumPy** and **Pandas** — numerical/data utilities

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app and API endpoints
│   │   ├── data/
│   │   │   ├── rbi.index           # Active FAISS index
│   │   │   ├── rbi_docs.json       # Metadata and stored chunks
│   │   │   └── staging/            # Staged index builds
│   │   └── services/
│   │       ├── rag_pipeline.py     # Retrieval and answer orchestration
│   │       ├── vector_store.py     # FAISS and embedding operations
│   │       ├── rbi_ingest.py       # RBI document processing
│   │       ├── rbi_scraper.py      # RBI PDF discovery
│   │       ├── rebuild_rbi_index.py # Staging index builder
│   │       ├── llm_service.py      # Groq client
│   │       ├── google_news_rss.py  # Google News RSS
│   │       └── youtube_news.py     # YouTube video aggregation
│   └── rebuild_rbi_index.py        # RBI index build entry point
├── frontend/
│   └── app.py                      # Streamlit UI
├── tests/
│   └── test_rbi_ingestion.py       # Focused ingestion/retrieval tests
├── .env.example                    # Environment variable names/placeholders
├── requirements.txt
└── README.md
```

## Windows setup

Use Python **3.11** (the deployment configuration targets Python 3.11.9). Run commands from the repository root in PowerShell.

1. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

   The first backend startup may need to download the `all-MiniLM-L6-v2` embedding model if it is not already cached.

3. Create a local environment file only if you do not already have one:

   ```powershell
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   ```

   Edit `.env` locally and replace the placeholders with your own credentials. **Never commit or share `.env`.** Keep an existing `.env` rather than overwriting it.

## Environment variables

The backend loads `.env` from the repository root. The `.env.example` file documents these variables:

| Variable | Required for | Description |
|---|---|---|
| `GROQ_API_KEY` | AI chat | Your Groq API key. Chat generation cannot work without it. |
| `GROQ_MODEL` | AI chat | Optional model selection; the service has a code default if omitted. |
| `YOUTUBE_API_KEY` | YouTube feed | YouTube Data API key. Without it, the YouTube route returns no videos. |
| `BANKING_NEWS_BACKEND_URL` | Frontend | Optional API base URL; defaults to `http://127.0.0.1:8000`. |

The Streamlit app reads `BANKING_NEWS_BACKEND_URL` from its process environment; it does not load the backend's `.env` itself. For a non-default backend URL, set it in the frontend PowerShell session before launching Streamlit:

```powershell
$env:BANKING_NEWS_BACKEND_URL = "http://127.0.0.1:8000"
```

## Run locally

Start the backend in one PowerShell window from the repository root:

```powershell
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`; interactive API documentation is at `http://127.0.0.1:8000/docs`.

Start the frontend in a second PowerShell window:

```powershell
.\venv\Scripts\Activate.ps1
streamlit run frontend/app.py
```

Streamlit prints the local browser URL when it starts.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Backend health/message |
| `GET` | `/news/google?limit=10` | Fetch Google News RSS results |
| `GET` | `/news/youtube?limit=5` | Fetch recent YouTube videos |
| `GET` | `/news/rbi?limit=5` | Discover RBI PDF documents |
| `POST` | `/chat?query=...` | Answer a question from the RBI RAG pipeline |

`/chat` accepts `query` as a query parameter and returns an `answer` and `sources` array. The current Streamlit UI displays the answer but does not yet render the returned source citations.

Example request from PowerShell:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/chat?query=What%20security%20controls%20apply%20to%20Commercial%20Banks%3F"
```

## Example questions

- What digital-payment security controls are specified for Commercial Banks?
- What controls are described in the Digital Payments E-mandate Framework?
- What digital-payment security controls are listed for Small Finance Banks?
- What security controls are described for Payments Banks?

Answers depend on the retrieved passages and the active corpus. Phrase questions with an institution type when asking about institution-specific regulations.

## Current limitations

- The active RBI corpus is a finite snapshot (currently 224 chunks from 20 source URLs), not a complete or continuously synchronized RBI archive.
- Current metadata includes digital-payment security directions and the e-mandate framework, but no titled digital-lending or MPC/monetary-policy document. Questions in those areas may not be answerable from the current index.
- Semantic retrieval can return passages that are related but incomplete or not representative of a whole document. The chatbot is not a substitute for checking the complete official direction.
- Institution-scope filtering is currently narrow; it specifically guards explicit Commercial Banks queries and does not provide comprehensive applicability analysis for every RBI entity category.
- Chatbot quality depends on retrieved context and Groq availability, credentials, quotas, and model limits.
- Google News RSS, YouTube, RBI document discovery, and automatic RBI ingestion require network access. YouTube additionally requires its API key.
- Google News and YouTube appear in the news dashboard, not in chatbot retrieval context.
- The frontend currently shows a citation placeholder instead of rendering chat source links.
- This project is an interview/demo application, not legal or financial advice.

## Future enhancements

- Expand and regularly refresh RBI corpus coverage, including digital lending and MPC/monetary-policy sources.
- Improve passage selection and retrieval evaluation for broad and institution-specific questions.
- Render source links and page-level citations in the frontend.
- Integrate news retrieval into chat only with clear source separation and tests.
- Add automated API and frontend integration tests, health checks, and improved error reporting.