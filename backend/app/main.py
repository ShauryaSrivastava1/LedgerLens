"""
Application entrypoint for Milestone 1: Foundation.

Scope: company master data + financial metrics + shareholding pattern CRUD.
No AI analysis, document ingestion, or scoring yet — those land in later
milestones on top of this schema.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    ai_reports,
    alerts,
    assistant,
    auth,
    companies,
    compare,
    documents,
    financials,
    portfolio,
    prices,
    search,
    timeline,
    watchlist,
)

# Table creation is NOT done at import time (that would force every process
# that imports this module — including the test suite — to have a live DB
# connection). Use `python -m app.init_db` for local-dev bootstrap, or
# Alembic migrations for anything beyond a throwaway dev environment.

app = FastAPI(
    title="Intelligent Equity Analysis Platform API",
    description=(
        "Evidence-based equity research assistant for Indian listed companies. "
        "Every conclusion the platform surfaces is expected to cite the "
        "underlying data — this API is the source of truth for that data."
    ),
    version="0.9.0-milestone9",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(financials.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(ai_reports.router)
app.include_router(assistant.router)
app.include_router(compare.router)
app.include_router(auth.router)
app.include_router(portfolio.router)
app.include_router(prices.router)
app.include_router(watchlist.router)
app.include_router(alerts.router)
app.include_router(timeline.router)


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "milestone": "9-ai-assistant"}
