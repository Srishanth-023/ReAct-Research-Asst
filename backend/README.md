# ReAct Academic Research Assistant — Backend API (`/backend`)

Python Flask REST API and Server-Sent Events (SSE) streaming engine for the **Automated Academic Research Assistant** reproducing Yao et al. (ICLR 2023).

---

## 1. Prerequisites
- **Python 3.11+** (`python --version`)
- Pip & Virtual environment support (`venv`)

---

## 2. Setup & Virtual Environment

1. **Navigate to backend directory**:
   ```powershell
   cd backend
   ```

2. **Create Python virtual environment**:
   ```powershell
   python -m venv venv
   ```

3. **Activate virtual environment**:
   - On Windows (PowerShell):
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install required dependencies**:
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 3. Environment Configuration (`.env`)

Copy the provided template `.env.example` to `.env`:
```powershell
cp .env.example .env
```

Open `.env` and configure your Anthropic Claude API key and preferred model:
```ini
# Anthropic API Key (Required for ReAct Agent execution)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-7-sonnet-20250219

# Server configuration
FLASK_APP=app.py
FLASK_ENV=development
PORT=5000

# Storage paths
CHROMA_PERSIST_DIR=./data/chroma
SQLITE_DB_PATH=./data/react_research.db
PDF_STORAGE_DIR=./data/pdfs
```

---

## 4. First-Run Database Initialization (Mandatory)

Before starting the server for the first time, you **MUST** explicitly initialize the relational schema and vector collection. Do not skip this step!

Run the standalone initialization script:
```powershell
python init_db.py
```
*Or via Flask CLI:*
```powershell
flask init-db
```

**What this does:**
1. Creates local data directories (`/backend/data/chroma`, `/backend/data/pdfs`, etc.).
2. Creates SQLite tables (`queries`, `trajectory_steps`, `papers`, `citations`) via `SQLAlchemy Base.metadata.create_all()`.
3. Calls `get_or_create_collection("research_papers")` in ChromaDB using `sentence-transformers` (`all-MiniLM-L6-v2`) embeddings.

---

## 5. Running the Backend Server

Start the Flask application:
```powershell
python app.py
```
*Or via Flask:*
```powershell
flask run --host=0.0.0.0 --port=5000
```

The API will start on **http://localhost:5000**.
- Health check: `GET http://localhost:5000/api/health`
- SSE Streaming Route: `POST http://localhost:5000/api/query/stream`

---

## 6. CORS Configuration
Flask-CORS (`flask_cors.CORS`) is pre-configured in `app.py` to allow cross-origin HTTP requests and Server-Sent Events from frontend development origins:
- `http://localhost:5173` (Vite Default)
- `http://127.0.0.1:5173`
- `http://localhost:3000`

If deploying to production or a custom port, update `CORS(app, resources={r"/api/*": {"origins": [...]}})` inside `app.py`.

---

## 7. Known Limitations & Architecture Notes
- **arXiv Search vs. Full-Text Search**: `search_arxiv` searches titles and abstracts across arXiv. Full-text prose semantic search becomes active inside ChromaDB once `fetch_paper` is invoked on a paper.
- **Semantic Scholar API**: Queries `https://api.semanticscholar.org/graph/v1/paper/search`. If `openAccessPdf` is null or if the free-tier rate limit is reached (`HTTP 429`), explicit observation feedback is returned so the ReAct agent adapts gracefully.
- **Repetition Guard**: Tracks the last two tool calls `(tool_name, tool_args)`. If identical, forces an intervention observation to prevent infinite reasoning loops.
- **Stopping Condition**: Enforces `MAX_STEPS = 10` by default.
- **SQLite Migrations**: SQLite is used directly without Alembic migrations for assignment scope. If you modify model columns in `models/schema.py`, delete `/backend/data/react_research.db` and re-run `python init_db.py`.
