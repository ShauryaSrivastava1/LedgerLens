# Intelligent Equity Analysis Platform

An evidence-based equity research assistant for Indian listed companies.
This is **not** a price-prediction tool — every conclusion the platform
eventually surfaces (green/red flags, moat scores, governance risk) is
required to cite the underlying data it came from.

This repo is being built milestone-by-milestone. Each milestone is
independently runnable and reviewed before the next one starts.

## Milestone 1 — Foundation (this delivery)

**Scope:** company master data, financial metrics, and shareholding pattern
— the core relational schema everything else (AI scoring, document
ingestion, comparisons) will sit on top of. Deliberately excludes AI,
document upload, and vector search — those are Milestone 2+, once this
schema is confirmed to be the right shape.

**What's included:**
- FastAPI backend with a full CRUD API for companies, financial metrics,
  and shareholding pattern
- PostgreSQL schema via SQLAlchemy models (`backend/app/models.py`)
- Pydantic request/response contracts, decoupled from the ORM
- 13 passing tests covering create/read/update/delete, duplicate
  prevention, and 404 handling
- Docker Compose stack (API + Postgres) for one-command local run

**What's NOT included yet (future milestones):**
- No live/automated price feed — prices only exist once someone uploads
  them. There's no scheduled job to keep them current
- Password reset / email verification (registration + login only)
- Recharts is still on the 2.x line (see Milestone 7) — a deliberate v3
  migration remains deferred

## Milestone 9 — AI Assistant

**Scope:** a grounded question-answering endpoint for a single company —
"why is this company risky?", "what does the evidence say about its
moat?" — built entirely on infrastructure Milestones 2 and 3 already
shipped. No new retrieval, embedding, LLM, or citation-verification code
paths; the only new logic is *what gets retrieved* (the question itself,
embedded and searched) and *how the answer is validated* before it's
returned.

**What's included (backend):**
- `POST /companies/{id}/assistant/ask` — takes a single `question` string
  (3–1000 chars), answers it grounded only in that company's financial
  metrics, shareholding pattern, price data, and semantically-retrieved
  document excerpts. No auth required, same as every other company
  research endpoint.
- `services/report_context.build_assistant_context()` — reuses
  `ReportContext` and the existing financial/shareholding/price summary
  formatters unchanged; the only difference from report generation's
  `build_context()` is that retrieval runs one embedding of the user's
  question against the `VectorStore`, not the five fixed analysis-topic
  queries.
- `services/assistant.answer_question()` — same shape as
  `report_generator.generate_report()` (build context → prompt → LLM →
  validate → verify citations), reusing `report_generator._extract_json`
  directly rather than duplicating JSON-fence stripping.
- `services/report_schema.py` gained `AssistantAnswerOutput`,
  `AssistantCitationItem`, and `verify_and_annotate_citations()` — the
  same "check what was retrieved, don't trust the prompt" verification
  Milestone 3 built for report flags, refactored around a shared
  `_citation_is_verified()` check so the two call sites can't quietly
  drift apart.
- 18 new tests (176 total): the deterministic insufficient-evidence path
  (no LLM call) when a company has nothing ingested, verified document and
  financial-metric citations, question-driven (not fixed-topic) retrieval,
  request validation, the missing-company 404, and — the one genuinely new
  behavior this milestone adds — a forced downgrade to the deterministic
  insufficient-evidence response whenever the model's citations don't
  actually verify, regardless of what the model itself claims.

**What's included (frontend):**
- **Ask the AI Assistant** panel on the company detail page
  (`AssistantPanel.tsx`) — a question box, a few example prompts, and the
  answer with citation chips reusing the platform's existing verified/
  unverified visual language (`AssistantCitationChip.tsx`, styled after
  `EvidenceChip.tsx` — teal for verified, amber for unverified, never
  hidden either way).
- Stateless on the frontend too: the panel shows only the most recent
  answer and never sends prior questions back to the API. Asking a new
  question doesn't reference the last one in any way.

**Design choices, worth your review:**

1. **Deterministic insufficient-evidence has two triggers, not one.**
   Like Milestone 3's report generator, a company with nothing ingested at
   all short-circuits before any LLM call. But an assistant answer can
   also fail *after* the LLM responds: if none of its citations verify
   against what was actually retrieved for this specific question, the
   response is discarded and replaced with the same deterministic
   fallback — even if the model set `insufficient_evidence: false` and
   sounded confident. "Every answer must contain citations" is enforced
   in code, not requested in a prompt and hoped for.

2. **Retrieval is intentionally scoped to one company, one question, no
   history.** The endpoint doesn't accept or store prior turns, and
   doesn't support cross-company comparison — asking it to compare two
   companies gets a same-company-only answer per the system prompt's
   rules, not a silent attempt to reach into another company's vectors.
   A multi-company conversational assistant is a materially different
   feature (session state, cross-company retrieval scoping) and was
   deliberately left out rather than half-built.

3. **No new tables.** An assistant answer isn't persisted — unlike
   `AIReport`, there's no history view for past questions. Each call is
   independent and reproducible from its own `context_snapshot`
   (document IDs, financial periods, and chunk count actually retrieved),
   the same reproducibility principle `AIReport.context_snapshot` exists
   for, just not written to a table since there's no report to look back
   at later.

## Milestone 8 — Export & Sharing

**Scope:** let people take data out of the platform — a PDF of an AI
report to save or share, and CSV exports of portfolio holdings and the
watchlist for use in a spreadsheet.

**What's included (backend):**
- `GET /companies/{id}/ai-reports/{report_id}/pdf` — renders the same
  data the JSON endpoint returns (scores, flags with evidence and
  citation-verified status, questions, risks, summary) as a downloadable
  PDF via reportlab's platypus API. No auth required, same as the JSON
  version — company research is public on this platform
- `GET /portfolio/export.csv`, `GET /watchlist/export.csv` — both
  authenticated, both plain stdlib `csv` output (no pandas needed for
  output this simple)
- 9 new tests (140 total): PDF generation (including the
  insufficient-evidence path, which has all-null scores and needs to
  render without crashing), CSV content and headers, auth requirements,
  empty-portfolio edge case

**What's included (frontend):**
- "Download PDF" link on the AI report detail view (plain `<a href>` —
  no JS needed, since the endpoint is public)
- "Export CSV" buttons on the portfolio and watchlist pages, which do
  need JS: an authenticated download can't use a plain link (no way to
  attach a bearer token to `<a href>`), so `lib/api.ts` gained a
  `downloadAuthenticatedFile` helper that fetches with the token, then
  triggers a browser save via a throwaway blob URL

**Design choices, worth your review:**

1. **The PDF mirrors the API response exactly**, not a prettied-up
   summary. Same scores, same flags, same `citation_verified` markers
   (shown as "verified" / "UNVERIFIED — treat with caution" next to each
   flag's citation). A export that could drift from what's actually
   stored and auditable would undermine the same principle Milestone 3's
   citation verification exists to protect.

2. **Both CSV exports use the stdlib `csv` module directly**, not a
   dataframe library. For a handful of explicit columns, writing them
   out directly makes it easy to see exactly what ends up in the file a
   user opens — no implicit type coercion or column reordering to debug.

3. **PDF export required a genuine edge case to be handled deliberately**:
   a report with no data on file has every score as `null` ("insufficient
   evidence" path from Milestone 3). The PDF generator has to render that
   report — as em dashes for missing scores — without crashing, not skip
   it. That's specifically covered in the test suite rather than assumed
   to work.

## Milestone 7 — Trend Charts + Company Timeline

**Scope:** two complements to everything already built. Charts, because
every milestone up to now deliberately kept data in tables until the
underlying numbers were confirmed correct — that verification is done,
so it's time to visualize trends instead of only listing figures. And a
company timeline, named directly in your original spec's feature list,
which merges documents, AI reports, and risk alerts into one
chronological narrative.

**What's included (backend):**
- `GET /companies/{id}/timeline` — merges `Document.uploaded_at`,
  `AIReport.generated_at`, and `RiskAlert.triggered_at` into one
  descending-order list. Deliberately narrow: financial metric and
  shareholding *additions* aren't timeline events, since they're data
  points already visible in their own trend charts, not something that
  "happened" in a narrative sense — this is the "what's the story of
  this company on the platform" view, not a full audit log
- 7 new tests (131 total) covering empty timelines, each event type
  individually, chronological ordering, and all three combined

**What's included (frontend):**
- Recharts added as a dependency (chosen for React-native API and clean
  Tailwind-adjacent styling; note below on version status)
- **Revenue/PAT bar chart** and **ROCE/ROE/margin line chart** above the
  financial metrics table
- **Price history line chart**, with a dashed reference line at your
  average buy price when you're logged in and hold that company
- **AI score history chart** (overall/governance/moat over time) above
  the report detail view
- **Timeline** section on every company page, showing the merged
  narrative from the new endpoint
- Every chart has a text fallback ("need at least two data points…")
  rather than rendering an empty or misleading chart with too little
  data

**Design choices, worth your review:**

1. **Timeline is deliberately narrow.** Only three event types
   (documents, AI reports, risk alerts) — not every financial metric or
   shareholding record added. Including those would turn a narrative
   view into a duplicate of the data tables that already exist for that
   purpose. If you want a fuller audit log later, that's a distinct
   feature from this timeline, not an extension of it.

2. **`recharts` is on the actively-maintained 2.x line (2.15.4), not
   3.x.** npm flags the whole 2.x branch as deprecated in favor of v3,
   which has breaking API changes. I chose to stay on 2.x for this
   milestone rather than risk an untested major-version migration —
   worth revisiting deliberately in a future milestone rather than as a
   side effect of adding charts.

3. **Charts refuse to render on insufficient data** (fewer than 2 points)
   and show a short explanatory line instead. A single-point trend chart
   is worse than no chart — it implies a shape that isn't there.

## Milestone 6 — Historical Price Ingestion + True Portfolio Valuation

**Scope:** ingest historical price data (the last data source from your
original spec's list) and use it to turn Milestone 5's cost-basis-only
portfolio into one with real mark-to-market value, plus feed price
context into AI report generation for valuation grounding.

**Why ingestion, not a live feed:** this environment can't reach a live
market-data API — no such domain is reachable from the sandbox this was
built in. Rather than fake a live feed or leave valuation unbuilt, prices
are ingested the same way documents are: uploaded (single point or CSV
bulk), timestamped, and clearly labeled with how stale they are. If you
deploy this with access to a real price API, swapping in a scheduled job
that calls `crud.add_price`/`bulk_add_prices` is straightforward — the
ingestion and valuation logic doesn't care where a price came from.

**What's included (backend):**
- `POST /companies/{id}/prices` (single point), `POST .../prices/bulk`
  (CSV upload — tolerant of several header/date-format conventions,
  reports row-level parse errors, skips already-priced dates on re-upload
  rather than failing the batch), `GET .../prices`, `GET .../prices/latest`
- `GET /portfolio/summary` now returns, per holding: `current_price`,
  `price_as_of`, `price_staleness_days`, `current_value`,
  `unrealized_pnl`, `unrealized_pnl_pct`, and `down_significantly_from_buy`
  (≤-15%) — all null when no price data exists for that company, never
  silently derived from cost basis. Portfolio totals are computed only
  from priced holdings, with `all_holdings_priced` telling the caller
  whether that total is complete
- AI report generation now includes a price/52-week-range section in the
  LLM's context, explicitly labeled as historical context for the
  valuation score, **not** a request to forecast — this platform doesn't
  predict prices, and the prompt says so
- 28 new tests (124 total): CSV parsing (multiple date formats, header
  aliases, malformed rows, BOM handling), price endpoints, and valuation
  math (fully priced, partially priced, stale price, down-significantly
  flag)

**What's included (frontend):**
- Price panel on each company page — CSV upload, latest price, recent
  history
- Portfolio page shows current value and unrealized P&L per holding
  alongside invested cost, with a visible "price N days old" warning
  when a holding's price data is stale, and "no price data" instead of
  a fabricated number when none exists

**Design choices, worth your review:**

1. **Nulls, not fallbacks, when price data is missing.** A holding
   without ingested price data gets `current_value: null`, not a value
   quietly equal to invested cost. The frontend shows "no price data"
   rather than a number that looks legitimate but isn't.

2. **Portfolio totals are explicit about partial coverage.**
   `total_current_value` sums only the holdings that have price data,
   and `all_holdings_priced` says whether that's everything or not — so
   a two-holding portfolio with only one priced company doesn't produce
   a total that looks complete when it isn't.

3. **The "down significantly" signal lives on the holding row, not as a
   persisted RiskAlert.** Milestone 5's alerts are discrete events
   ("something changed just now"); "you're down 20% from your buy
   price" is a continuous condition tied to one user's personal cost
   basis, not a company-level event. Forcing it into the shared,
   company-scoped alert table would have been a worse fit than exposing
   it as a computed field on the portfolio response, which is what
   this does.

4. **Bulk CSV upload skips duplicate dates instead of failing.**
   Re-uploading an overlapping export (e.g. this month's file that
   includes last month's tail) is a normal workflow, so it's handled
   as "already have it," not an error requiring the person to manually
   diff and trim their file first.

## Milestone 5 — Authentication, Portfolio, Watchlist, Risk Alerts

**Scope:** the first milestone with a concept of "who's asking." Company
research (companies, documents, reports, comparisons) stays open to
everyone, as it has since Milestone 1 — auth is scoped specifically to
the features that are inherently personal: portfolio holdings, watchlist,
and per-user alert acknowledgment.

**What's included (backend):**
- `POST /auth/register`, `POST /auth/login` (OAuth2 password flow), `GET /auth/me`
- `POST/GET/PATCH/DELETE /portfolio/holdings`, `GET /portfolio/summary`
  (invested amount + sector allocation, cost-basis)
- `POST/GET/DELETE /watchlist`
- `GET /companies/{id}/risk-alerts` (public, part of company research)
- `GET /me/alerts` (authenticated, aggregated across portfolio +
  watchlist, with per-user acknowledgment) and `POST /alerts/{id}/acknowledge`
- Risk alerts generate automatically — no polling job. Saving a new
  shareholding record checks it against the previous one for a pledge
  increase or promoter-holding decrease; generating a new AI report
  checks it against the previous one for a governance or overall score
  drop
- 41 new tests (96 total): auth flows, ownership checks (a user can't
  touch another user's holdings/watchlist), threshold-crossing logic for
  every alert type, and the full aggregation + acknowledgment flow

**What's included (frontend):**
- Login/register page, auth persisted via a bearer token
- **Portfolio** (`/portfolio`) — add/remove holdings, invested-amount
  summary, sector allocation bar chart
- **Watchlist** (`/watchlist`) — add from any company page, remove here
- **Alerts** (`/alerts`) — grouped by needs-review / acknowledged
- Watchlist button and a company's alert history now show on its detail
  page too

**Design choices, worth your review:**

1. **Auth is scoped narrowly, on purpose.** Every endpoint from
   Milestones 1–4 remains open. Retrofitting auth onto company research
   now would be a breaking change to everything already built, for a
   feature (personal portfolio/watchlist) that doesn't need it. If the
   platform later needs to gate research behind accounts too, that's a
   deliberate, separate decision — not a side effect of this milestone.

2. **Portfolio allocation is cost-basis, not mark-to-market**, and the
   API says so directly (`PortfolioSummaryOut.note`) rather than
   presenting an invested-amount percentage as if it were a live
   portfolio weight. There's no price feed yet — pretending otherwise
   would be a quiet inaccuracy in a platform whose entire premise is not
   doing that.

3. **Risk alerts fire on save, not on a schedule.** A pledge increase or
   score drop is visible the moment the triggering data is saved, with
   no polling delay — and no risk of alerts silently falling behind if a
   background job stalls.

4. **Alert acknowledgment is per-user, alerts themselves are
   company-scoped.** Two users tracking the same company see the same
   alert but can independently mark it reviewed — modeled as a separate
   `AlertAcknowledgment` join table rather than a single flag on the
   alert, which would have let one user's "seen it" hide the alert from
   everyone else.

5. **Thresholds are conservative and documented, not tuned.** A ≥0.5pp
   pledge increase, a ≥1pp promoter-holding drop, a ≥10-point score drop
   — reasonable starting points, explicitly called out in
   `services/risk_alerts.py` as worth revisiting once there's real usage
   data on what's noise versus signal.

## Milestone 4 — Compare Companies + Frontend Dashboard (v1)

**Scope:** a comparison endpoint that puts growth, margins, leverage, and
the AI report's scores for multiple companies side by side, plus a real
Next.js dashboard on top of everything built in Milestones 1–3 — company
list, upload flow, metric-candidate review, AI report view, and company
comparison.

**What's included (backend):**
- `GET /compare?symbols=A,B,C` — up to 10 companies, each row showing
  latest-period financials, period-over-period growth, shareholding, and
  the latest AI report's scores (or nulls if a company has none of that
  data yet — never fabricated)
- 7 new backend tests (55 total) covering growth math, missing data,
  duplicate/too-many-symbol rejection, and AI-score inclusion

**What's included (frontend, `/frontend`):**
- Next.js 14 (App Router) + TypeScript + Tailwind, calling the FastAPI
  backend directly from the browser
- **Dashboard** (`/`) — company list, add-company form
- **Company detail** (`/companies/[id]`) — shareholding, financial
  metrics table, document upload + processing status, metric-candidate
  review (accept/reject/promote), AI report generation and history
- **Compare** (`/compare`) — pick companies, see them side by side
- A verified production build (`npm run build`) with zero type errors

**Design choices, worth your review:**

1. **Growth is computed from same-period-type pairs.** Comparing the two
   most recent ANNUAL rows (falling back to QUARTERLY only if a company
   has no annual data) avoids a nonsensical "growth" number from
   comparing a quarter against a year.

2. **The frontend has a deliberate visual identity, not a default
   dashboard template.** It's built as a "ledger" — paper-toned
   background, a serif display face for headings, monospace for every
   number (so figures align the way they would in an actual financial
   statement), and a signature element: every flag in an AI report
   carries a small citation chip (`[p.47]`) styled like a footnote
   marker — teal if the citation checks out against what the model was
   actually given, amber with a warning if it doesn't. That's the same
   `citation_verified` field from Milestone 3's API, made visible rather
   than buried in a JSON response.

3. **Client-side fetching, not a proxy layer.** Pages call the FastAPI
   backend directly via `NEXT_PUBLIC_API_URL`. Simpler for this stage;
   if auth is added later (flagged as a gap), that's the natural point to
   introduce a server-side API layer instead.

4. **No charts yet.** Financial metrics render as a table, not a trend
   line. Tables are more information-dense and easier to get exactly
   right first; a charting library is a reasonable Milestone 5+ addition
   once you've confirmed the data being shown is what you want.

## Running the frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # point at your running backend
npm run dev
```

Open http://localhost:3000. The backend must be running (`docker compose
up` from the project root, or `uvicorn app.main:app` locally) for pages
to load data — the dashboard shows a clear error message rather than a
blank page if it can't reach the API.

**Note:** the build fetches Source Serif 4, Inter, and IBM Plex Mono from
Google Fonts at build time via `next/font/google` — this needs outbound
internet access during `npm run build`/`npm run dev`. If you're building
in a fully offline environment, swap these for locally-hosted font files
using `next/font/local` instead.

## Milestone 3 — AI Report Generation

**Scope:** wire an LLM to the retrieval pipeline built in Milestone 2.
Semantic search supplies grounded context (financial metrics +
shareholding trend + retrieved document excerpts across five fixed
analysis topics); the LLM is constrained to answer only from that
context and to cite a document+page or a metric+period for every flag;
the output is validated, cross-checked, and stored. Also closes the loop
on Milestone 2's metric candidates: reviewed candidates can now be
promoted into `FinancialMetric` with one call.

**What's included:**
- `POST /companies/{id}/ai-reports` — generates a new report (on-demand,
  synchronous — see caveat below) and stores it
- `GET .../ai-reports`, `GET .../ai-reports/{id}` — historical scores,
  most recent first (the "Historical Score" / "Company Timeline" data)
- `POST .../metric-candidates/{id}/promote` — writes an accepted
  candidate into `FinancialMetric`, linked back for audit purposes
- Provider-agnostic LLM interface (`app/services/llm/`) with Anthropic
  and OpenAI adapters implemented; Gemini/local-LLM need one more small
  adapter class each, nothing else changes
- 13 new tests (48 total): context building, citation verification
  (including a fabricated-citation case that must be flagged, not
  trusted), JSON-parsing edge cases, and the full HTTP flow

**Deliberate design choices, worth your review:**

1. **Citations are cross-checked against what was actually retrieved,
   not just requested in the prompt.** Every flag the LLM returns states
   a `document_id`+`page_number` or a `period`; before storage, each is
   checked against the exact set of document IDs and periods that were
   in that report's context. A citation that doesn't match gets
   `citation_verified: false` — visible to the reviewer, not silently
   dropped or silently trusted. A prompt instruction ("only cite what
   you're given") is not a guarantee, so this is enforced in code.
   The test suite exercises this directly: the fake LLM always emits one
   fabricated citation, and the test confirms it comes back unverified.

2. **`context_snapshot` is stored on every report** — the exact document
   IDs, pages, and financial periods that went into it. This is what
   "every AI decision must be reproducible" means concretely here: you
   can see precisely what the model was and wasn't shown for any given
   score.

3. **Empty evidence never reaches the LLM.** If a company has no
   financial metrics and no ingested documents, the report is generated
   deterministically ("I don't have enough evidence...") without a model
   call — cheaper, faster, and there's nothing for the model to
   hallucinate about in the first place.

4. **Report generation is synchronous, not a background task**, unlike
   document processing. It's a single LLM round trip rather than a
   multi-step pipeline, so the wait is short and a background-task
   + polling flow would add complexity without much benefit at this
   stage. Worth revisiting if reports start covering many more topics
   or chaining multiple LLM calls.

5. **Promotion is a separate, deliberate step from acceptance**, and
   requires the caller to state the target period explicitly rather than
   inferring it from the source document. A figure inside an annual
   report might belong to a comparison year, not the report's own period
   — guessing that would undermine the same "no black-box decisions"
   principle the candidate-review system exists to protect.

**Caveat for real use:** the embedding model download (Milestone 2) and
whichever LLM provider you configure both need outbound internet access
and, for the LLM, a valid API key (`ANTHROPIC_API_KEY` or
`OPENAI_API_KEY`, selected via `LLM_PROVIDER`). Tests never call a real
LLM or download a real embedding model — both are swapped for
deterministic fakes.

## Milestone 2 — Document Ingestion Pipeline

**Scope:** upload a PDF → extract text → chunk it → embed the chunks →
store vectors in ChromaDB + chunk text in Postgres (for citations) → run a
conservative first-pass regex extractor that flags possible financial
figures for human review. Semantic search over ingested documents is
included since it's needed to sanity-check the pipeline end-to-end, and
it's the exact retrieval step the AI assistant milestone will reuse.

**What's included:**
- `POST /companies/{id}/documents` — PDF upload, processed in a background
  task (extract → chunk → embed → store)
- `GET .../documents`, `GET .../documents/{id}`, `GET .../documents/{id}/chunks`
- `GET .../documents/{id}/metric-candidates` — figures the extractor found,
  each with its source snippet, page number, and a confidence score
- `POST .../metric-candidates/{id}/accept` / `/reject` — human review gate
- `GET /companies/{id}/search?q=...` — semantic search over a company's
  ingested chunks, returns citeable results (document, page, snippet)
- 22 new tests (35 total), covering chunking edge cases, the extraction
  regex (including a caught-and-fixed false positive — see below), the
  full pipeline end-to-end, and the HTTP layer

**Deliberate design choices, worth your review:**

1. **Extracted metrics are never auto-written to `FinancialMetric`.**
   They land in a separate `ExtractedMetricCandidate` table with
   `PENDING_REVIEW` status, the exact source snippet, page number, and a
   confidence score. Promoting an accepted candidate into the verified
   `FinancialMetric` table (Milestone 1) is currently a manual step. This
   is the most direct implementation of "no hallucinations" / "no
   black-box decisions" from your spec — a regex guessing a number from
   unstructured text is categorically not the same thing as a verified
   metric, and the two must never blur together.

2. **The extractor is regex-based, not LLM-based, on purpose for this
   milestone.** It's cheap, deterministic, and easy to unit test — good
   properties for a first pass. It's also fragile: while testing it, it
   initially misread "ROCE for **FY26** was 24.3%" as ROCE = 26, because
   "FY26" is a digit sequence that sits between the label and the real
   number. Fixed by blanking fiscal-year mentions before matching (see
   `metric_extraction.py`), and a regression test now locks that in.
   This kind of near-miss is exactly why every candidate carries a
   confidence score and requires human acceptance rather than being
   trusted outright — and why an LLM-based extractor (same review gate)
   is worth considering for a later milestone once real annual reports
   are run through this.

3. **Chunks never span pages.** A chunk's `page_number` is always
   unambiguous, which matters once the AI assistant starts citing
   "page 47" back to a user.

4. **No OCR fallback yet.** Scanned/image-only PDFs will extract as
   empty text per page and the document will end up processed with zero
   chunks, not silently wrong data. Flagged as a gap rather than
   papered over — OCR (pytesseract) is a reasonable Milestone 3+ add.

5. **Background processing uses FastAPI's `BackgroundTasks`, not a task
   queue.** Fine for now; won't survive an API process restart or scale
   past one worker. Noted in the code as the point where you'd want to
   swap in Celery/RQ once ingestion volume justifies it.

## Architecture (through Milestone 3)

```
                     ┌─────────────────┐
   HTTP clients ───▶ │   FastAPI app    │
                      │  app/main.py     │
                      └────────┬─────────┘
                               │
       ┌────────────┬──────────┼──────────┬───────────────┐
       │            │          │          │               │
┌──────┴──────┐┌────┴────┐┌────┴────┐┌────┴────┐  ┌────────┴────────┐
│companies.py ││financials││documents││search.py│  │ai_reports.py    │
│(Milestone 1)││ .py (M1) ││.py (M2) ││  (M2)   │  │(Milestone 3)     │
└──────┬──────┘└────┬────┘└────┬────┘└────┬────┘  └────────┬────────┘
       │             │          │          │                │
       └─────┬───────┴─────┬────┴────┬─────┴────────┬───────┘
             │              │         │              │
      ┌──────┴──────┐┌──────┴──────┐┌─┴──────────┐┌──┴─────────────┐
      │   crud.py     ││  services/  ││ services/    ││ services/         │
      │ (Postgres)     ││  ingestion  ││ vector_store ││ report_context    │
      └──────┬──────┘│  pipeline   ││ embeddings   ││ report_generator   │
             │        └──────┬──────┘└─┬──────────┘│ report_schema      │
             │                │         │           │ llm/ (Anthropic,   │
      ┌──────┴──────┐  ┌──────┴──────┐  │           │      OpenAI)       │
      │  PostgreSQL   │  │  ChromaDB    │◀──────────┘  └──────────────────┘
      │ (companies,   │  │ (chunk       │
      │  metrics,     │  │  embeddings) │
      │  documents,    │  └─────────────┘
      │  chunks,       │
      │  candidates,   │
      │  ai_reports)   │
      └──────────────┘
```

AI report generation flow (Milestone 3):

```
POST /companies/{id}/ai-reports
        │
        ▼
 has any financial metrics or ingested documents?
        │
   ┌────┴────┐
   │ NO       │──▶ deterministic "insufficient evidence" report (no LLM call)
   └────┬────┘
        │ YES
        ▼
 build_context(): format financial/shareholding summaries +
                  run 5 fixed topic queries against the vector store
        │
        ▼
 construct prompt (system rules + context) ──▶ llm_client.complete()
        │
        ▼
 parse JSON, validate against LLMReportOutput schema
        │
        ▼
 verify_and_annotate_flags(): does each cited document_id/period
 actually appear in the context we sent? mark citation_verified
        │
        ▼
 store as AIReport (scores, flags, questions, context_snapshot)
```

Design choices worth flagging for review:
- **Wide financial-metrics table** (one row per company per period, ~20
  metric columns) rather than a fully normalized metric-name/value table.
  Trades some schema rigidity for fast trend queries, which the AI report
  generator will hit constantly in later milestones. Worth revisiting if
  the metric list grows past what's listed in the spec.
- **Shareholding kept in its own table**, not merged into financial
  metrics, since it's sourced from a different filing on a different
  cadence.
- **No AI/document tables yet** — adding them now would mean guessing
  their shape before Milestone 2's actual ingestion pipeline is designed.

## Running it

```bash
# From the project root
docker compose up --build
```

- API: http://localhost:8000
- Interactive docs (Swagger): http://localhost:8000/docs

First run only, create the tables:
```bash
docker compose exec api python -m app.init_db
```

## Running tests

Tests use an isolated SQLite DB, so no Postgres/Docker needed:

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Example usage

```bash
# Create a company
curl -X POST http://localhost:8000/companies \
  -H "Content-Type: application/json" \
  -d '{"symbol": "DMART", "name": "Avenue Supermarts Ltd", "sector": "Retail"}'

# Add a quarterly financial metric
curl -X POST http://localhost:8000/companies/{company_id}/financial-metrics \
  -H "Content-Type: application/json" \
  -d '{
    "period_type": "QUARTERLY",
    "period_end_date": "2026-03-31",
    "fiscal_year": "FY2025-26",
    "revenue": 12500000000,
    "roce": 22.5,
    "receivable_days": 18.4
  }'

# Fetch company with full history
curl http://localhost:8000/companies/{company_id}

# Upload an annual report PDF
curl -X POST http://localhost:8000/companies/{company_id}/documents \
  -F "file=@annual_report.pdf" \
  -F "document_type=ANNUAL_REPORT"

# Check processing status
curl http://localhost:8000/companies/{company_id}/documents/{document_id}

# Review what the extractor flagged
curl http://localhost:8000/companies/{company_id}/documents/{document_id}/metric-candidates

# Accept a candidate (marks it reviewed; promoting it into FinancialMetric
# is a separate manual call to the Milestone 1 endpoint for now)
curl -X POST http://localhost:8000/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate_id}/accept

# Semantic search across a company's ingested documents
curl "http://localhost:8000/companies/{company_id}/search?q=promoter+pledging"

# Generate an AI report (needs LLM_PROVIDER + API key configured)
curl -X POST http://localhost:8000/companies/{company_id}/ai-reports

# View report history / timeline
curl http://localhost:8000/companies/{company_id}/ai-reports

# Ask the AI Assistant a grounded question about one company
curl -X POST http://localhost:8000/companies/{company_id}/assistant/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Why is promoter pledging a concern for this company?"}'

# Promote an accepted metric candidate into FinancialMetric
curl -X POST http://localhost:8000/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate_id}/promote \
  -H "Content-Type: application/json" \
  -d '{"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25"}'

# Compare companies
curl "http://localhost:8000/compare?symbols=DMART,TRENT"

# Register and log in
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "investor@example.com", "password": "correcthorsebattery"}'

curl -X POST http://localhost:8000/auth/login \
  -d "username=investor@example.com&password=correcthorsebattery"

# Add a holding (needs the access_token from login/register)
curl -X POST http://localhost:8000/portfolio/holdings \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"company_id": "<id>", "quantity": "10", "average_buy_price": "4200"}'

curl http://localhost:8000/portfolio/summary -H "Authorization: Bearer <token>"

# Watchlist and alerts
curl -X POST http://localhost:8000/watchlist \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"company_id": "<id>"}'

curl http://localhost:8000/me/alerts -H "Authorization: Bearer <token>"

# Ingest price data (single point or CSV bulk)
curl -X POST http://localhost:8000/companies/{company_id}/prices \
  -H "Content-Type: application/json" \
  -d '{"price_date": "2026-08-01", "close_price": "4250.50"}'

curl -X POST http://localhost:8000/companies/{company_id}/prices/bulk \
  -F "file=@nse_history.csv"

# Portfolio summary now includes mark-to-market fields when price data exists
curl http://localhost:8000/portfolio/summary -H "Authorization: Bearer <token>"

# Company timeline (documents, AI reports, risk alerts, merged and sorted)
curl http://localhost:8000/companies/{company_id}/timeline

# Download an AI report as PDF
curl -o report.pdf http://localhost:8000/companies/{company_id}/ai-reports/{report_id}/pdf

# Export portfolio / watchlist as CSV
curl -o portfolio.csv http://localhost:8000/portfolio/export.csv -H "Authorization: Bearer <token>"
curl -o watchlist.csv http://localhost:8000/watchlist/export.csv -H "Authorization: Bearer <token>"
```

**First real-document caveat:** the embedding model (`all-MiniLM-L6-v2`)
downloads from Hugging Face the first time it's used, so the first
document processed after a fresh container start will be slower and
needs outbound internet access. Subsequent runs use the cached model.
AI report generation needs `LLM_PROVIDER` set (`anthropic` or `openai`)
and the matching API key. Set `JWT_SECRET_KEY` to something real before
deploying anywhere but local dev — the default is intentionally an
obvious placeholder.

## Proposed next milestone (pending your approval)

Milestone 9 (above) delivered the single-company grounded AI Assistant.
Two things were deliberately left out of it, worth deciding on next:

- **Conversation memory / multi-turn chat.** Milestone 9's assistant is
  stateless by design (each question is answered independently, matching
  your "no black-box, fully auditable" principle from earlier milestones).
  A real chat experience — follow-up questions like "what about last
  year?" that implicitly reference a prior answer — needs a session/
  history model and a decision about what happens when history and fresh
  retrieval disagree. That's a meaningfully different feature, not a small
  addition to what's here.
- **Cross-company comparison inside the assistant** (e.g. "compare VMM and
  DMart" as a natural-language question, rather than the existing
  `/compare` endpoint's structured side-by-side view). Retrieval would
  need to span multiple companies' vector-store partitions and the
  citation-verification logic would need to track which company each
  citation belongs to — straightforward extensions of what's here, but
  deliberately out of scope until the single-company version is reviewed.

Also still pending from Milestone 7: the deliberate `recharts` v3
migration (currently on the actively-maintained but deprecated 2.x line).

Let me know if you want changes to the Milestone 9 API/frontend before
building further on top of it, or if you'd like to reshape what comes
next.
