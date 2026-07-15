# ReAct: Synergizing Reasoning and Acting in Language Models
## Automated Academic & Scientific Research Assistant (Full-Stack Web Application)

An end-to-end full-stack web application reproducing and demonstrating the **ReAct** (Reasoning + Acting) paradigm from **Yao et al. (ICLR 2023)** applied to real-world academic research. 

Instead of isolating numeric values or reading only abstracts, this assistant automatically **retrieves, downloads, ingests, and chunks full-text PDF research papers** (`pdfplumber` + `PyMuPDF`), indexes them into a local **ChromaDB vector store** (`sentence-transformers` `all-MiniLM-L6-v2`), cross-checks claims via **RAG semantic search over prose**, computes quantitative metrics safely via **Sympy**, and outputs traceable final reports with explicit `(paper_id, page X)` citations.

---

## Architecture & Project Structure

The project is strictly separated into decoupled backend and frontend folders:

```
ReAct-Research-Asst/
├── README.md                   # Root quickstart (this file)
├── ARCHITECTURE.md             # In-depth technical architecture & design specification
├── backend/                    # Python Flask + SQLAlchemy + Chroma + ReAct Engine
│   ├── app.py                  # Flask entrypoint & CORS configuration
│   ├── init_db.py              # Mandatory standalone DB & Vector Store init script
│   ├── config.py               # Environment & limit settings
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Backend env template
│   ├── models/schema.py        # SQLAlchemy models (Query, TrajectoryStep, Paper, Citation)
│   ├── database/               # Session management & get_or_create_collection helper
│   ├── services/               # PDF Ingester, arXiv Atom API, Semantic Scholar Graph API
│   ├── tools/                  # Action Space definitions (search_arxiv, fetch_paper, etc.)
│   └── react/                  # Core ReAct Engine, 4 Ablation Modes, and SSE route
└── frontend/                   # React 18 + Vite + Modern Glassmorphic UI
    ├── package.json
    ├── vite.config.js
    ├── index.html
    ├── .env.example
    └── src/                    # TraceView, Mode Selector, Sources Panel, History Inspector
```

---

## Quickstart Guide

### 1. Backend Setup & Initialization

1. Open a terminal and navigate to `/backend`:
   ```powershell
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # Windows PowerShell
   # source venv/bin/activate    # macOS/Linux
   ```
3. Install dependencies:
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Configure environment variables (`.env`):
   ```powershell
   cp .env.example .env
   ```
   Open `backend/.env` and insert your `ANTHROPIC_API_KEY`.

5. **Run the mandatory database initialization command once**:
   ```powershell
   python init_db.py
   ```
   *This creates the SQLite schema (`react_research.db`) and initializes the local ChromaDB vector store collection (`research_papers`).*

6. Start the Flask server:
   ```powershell
   python app.py
   ```
   *The backend runs on **http://localhost:5000**.*

---

### 2. Frontend Setup & Launch

1. Open a new terminal and navigate to `/frontend`:
   ```powershell
   cd frontend
   ```
2. Install Node dependencies:
   ```powershell
   npm install
   ```
3. Create environment file:
   ```powershell
   cp .env.example .env
   ```
4. Start the Vite development server:
   ```powershell
   npm run dev
   ```
   *The interactive web interface runs on **http://localhost:5173**.*

---

## Core ReAct Action Space

The agent operates over an explicit, restricted action space designed after Yao et al. (2023):
- `search_arxiv(query)`: Query arXiv API, returning top candidate papers with titles, abstracts, and years.
- `search_semantic_scholar(query)`: Fallback/supplement search with full-text availability status (`openAccessPdf` null checks).
- `fetch_paper(paper_id)`: Download PDF, parse full prose text, chunk by section heuristics (`Intro`, `Methodology`, `Results`, etc.), and index into ChromaDB (idempotent).
- `retrieve_context(paper_id, query)`: Semantic RAG search within one paper's chunks, returning passages with page numbers.
- `retrieve_context_all(query)`: Semantic RAG search across all indexed papers in the current session (for cross-paper synthesis).
- `calculate(expression)`: Safe algebraic/numeric evaluation via Sympy.
- `finish(answer)`: Terminates the loop, returning the final synthesized report with citations.

---

## Key Features & Demo Highlights

- **Real-Time SSE Streaming Trace**: Watch the agent interleave `Thought`, `Action`, and `Observation` incrementally as events happen live.
- **Live Ablation Mode Toggle**: Switch between `ReAct`, `CoT-only`, `Act-only`, and `Standard` on the navbar. Demonstrates how Chain-of-Thought isolated from full texts risks factual or numerical hallucination—reproducing the original paper's core findings.
- **Repetition Guard & Step Limits**: Automatically catches repeated tool invocations (`tool_name` + `tool_args`) to break reasoning loops, enforcing a safe `MAX_STEPS = 10` ceiling.
- **Interactive Sources & Citations**: Click any `(paper_id, page X)` citation pill in the final answer to inspect the exact RAG prose chunks and paper metadata in the right-hand **Sources Panel**.

---

## Documentation Links
- [System & Technical Architecture (`ARCHITECTURE.md`)](./ARCHITECTURE.md)
- [Backend Documentation (`backend/README.md`)](./backend/README.md)
- [Frontend Documentation (`frontend/README.md`)](./frontend/README.md)
