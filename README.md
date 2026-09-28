# Agentic PowerPoint Design Assistant

A privacy-focused PowerPoint design-retrieval demo. It compares slide structure without placing raw textbox content in embeddings, then recommends visually compatible slides from a local reference library.

## Current demo flow

```text
Upload PPTX
→ render uploaded slides as PNG previews
→ extract structural metadata
→ convert metadata into text descriptions
→ generate local MiniLM embeddings
→ retrieve and rerank PostgreSQL/pgvector references
→ preview, select, and download a recommended reference design
```

The embedding description includes element types, positions, sizes, typography metadata, character counts, and table dimensions. It does **not** include raw textbox text.

Retrieval combines embedding similarity with geometry, element counts, and stricter layout rules for:

- Tables and charts
- Table row and column counts
- Two- and three-column composition
- KPI value count
- Repeated process-step count
- Prominent images

The API returns the strongest compatible matches. It may return only one result when only one reference is sufficiently compatible. If no strict match exists, it returns the closest fallback.

## Project layout

```text
frontend/            Next.js, React, and Tailwind UI
backend/             FastAPI, Pydantic, PPTX parsing, embeddings, and retrieval
reference-slides/    Reference PPTX design library
test-presentations/  Demo input decks for common layouts
storage/uploads/     Uploaded PPTX files
storage/previews/    Generated uploaded/reference slide thumbnails
compose.yml          PostgreSQL and pgvector service
```

## Requirements

- Node.js and npm
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop
- LibreOffice (`soffice`) for PPTX-to-PDF conversion
- Poppler (`pdftoppm`) for PNG thumbnails

On macOS with Homebrew:

```bash
brew install --cask libreoffice
brew install poppler
```

You can set absolute executable paths with `SOFFICE_PATH` and `PDFTOPPM_PATH` in `backend/.env` if they are not available on `PATH`.

## 1. Start PostgreSQL

From the project root:

```bash
docker compose up -d postgres
```

PostgreSQL is exposed on host port `5433` to avoid conflicts with a local server using `5432`.

## 2. Set up and start the backend

Open a terminal in VS Code:

```bash
cd backend
cp .env.example .env
uv sync --extra dev
uv run beautify-slides init-db
uv run uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Keep this terminal open.

`GROQ_API_KEY` is optional for the current structural-retrieval demo. The current upload and recommendation flow uses local embeddings and does not call Groq.

## 3. Index reference slides

Place any number of `.pptx` files in `reference-slides/`. Each slide is indexed independently, so decks may contain different numbers of slides.

From `backend/` run:

```bash
uv run beautify-slides ingest-references
```

Run this command again after adding or replacing reference files. The first run downloads `sentence-transformers/all-MiniLM-L6-v2`; later runs use the local cache.

## 4. Set up and start the frontend

Open a second terminal:

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

The frontend uses Node.js and does not share the backend Python virtual environment.

## Demo inputs

The `test-presentations/` folder includes:

- `01-table-layout.pptx` — three-column table
- `02-two-column-layout.pptx` — two-column text layout
- `03-three-kpi-layout.pptx` — three KPI cards
- `04-four-step-process.pptx` — four-step process/timeline
- `05-title-and-body-layout.pptx` — title and body layout

## Tests

Backend:

```bash
cd backend
uv run pytest -q
uv run ruff check app tests
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

## Current limitations

- Recommendations use structural metadata rather than raw slide text.
- Abstract semantic labels such as `comparison`, `timeline`, or `problem-solution` are not implemented yet.
- LangGraph orchestration and a design-planning agent are not implemented yet.
- Groq is configured but is not required by the current retrieval workflow.
- Selecting a recommendation downloads its source reference PPTX; the system does not yet transfer that design onto the uploaded content.
- There is no automated visual critic or revision loop yet.
