# LedgerLens

Fundamental equity research and portfolio tracking web app for Indian stocks. Built with FastAPI, PostgreSQL, ChromaDB, and Next.js.

## What it does

- **Company & Financials CRUD:** Stores company fundamentals (revenue, margins, ROCE, ROE, receivable days) and quarterly shareholding patterns in PostgreSQL.
- **PDF Filing Ingestion:** Uploads annual reports/presentations, splits text by page, embeds chunks into ChromaDB, and runs a regex pass to flag financial numbers for manual review before saving to the main tables.
- **Grounded AI Reports & Q&A:** Uses OpenAI or Anthropic to generate risk scores, red/green flags, and answers to company questions. Every claim must include a document page or metric period, which gets cross-checked against the retrieved context before being shown in the UI or exported to PDF.
- **Portfolio, Watchlist & Alerts:** JWT auth for personal holdings and watchlists, CSV historical price uploads with staleness tracking, peer comparison (`/compare`), trend charts, and automatic alerts on promoter pledge spikes or score drops.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, ChromaDB, ReportLab, Pytest (176 tests)
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts
- **LLM / Embeddings:** OpenAI / Anthropic APIs, `sentence-transformers` (`all-MiniLM-L6-v2`)

## Local Setup

### Backend & Database
```bash
docker compose up --build
docker compose exec api python -m app.init_db
