# ReAct Academic Research Assistant — Frontend SPA (`/frontend`)

React 18 + Vite interactive frontend web application for the **ReAct Automated Academic Research Assistant** (reproducing Yao et al., ICLR 2023).

---

## 1. Prerequisites
- **Node.js 18+** (`node -v`)
- **npm** (`npm -v`)

---

## 2. Setup & Installation

1. **Navigate to frontend directory**:
   ```powershell
   cd frontend
   ```

2. **Install node dependencies**:
   ```powershell
   npm install
   ```
   *(Includes `lucide-react` icons and standard React/Vite packages).*

---

## 3. Environment Configuration (`.env`)

Copy the provided `.env.example` to `.env`:
```powershell
cp .env.example .env
```

Ensure `VITE_API_BASE_URL` points to your running Flask backend API:
```ini
VITE_API_BASE_URL=http://localhost:5000/api
```

---

## 4. Running Locally (`npm run dev`)

Start the Vite development server:
```powershell
npm run dev
```

Open your browser at **http://localhost:5173**.

---

## 5. UI Features & Demo Highlights

- **Live SSE Streaming Trace (`TraceView`)**:
  - Consumes incremental Server-Sent Events from `POST /api/query/stream`.
  - Distinguishes **Thought** (italicized, purple/slate glassmorphic card), **Action** (colored badge, tool name, and expandable JSON arguments box), and **Observation** (bordered green/amber box with source snippets and tool attribution).
- **Comparative Ablation Mode Selector (`Header`)**:
  - Easily toggle between `ReAct` (full loop), `CoT-only` (reasoning without tools), `Act-only` (tools without reasoning), and `Standard` (zero-shot) on the same query to demonstrate the core ablation findings of Yao et al. (2023). Hover over any toggle for a comprehensive educational tooltip.
- **Interactive Citations (`FinalAnswer`)**:
  - Citations formatted like `(2210.03629, page 3)` or `(PaperTitle, page X)` render as interactive purple pills. Clicking any citation opens the right-hand **Sources Panel** directly focused on that paper's chunks.
- **Right-Hand Sources Panel (`SourcesPanel`)**:
  - Lists all full-text indexed papers with ChromaDB chunk counts, author details, and direct external links to arXiv mirrors (`export.arxiv.org`/`arxiv.org`) and Semantic Scholar graph records.
- **SQLite Query History Inspector (`HistoryModal`)**:
  - Click the **History** button in the navbar to inspect all past queries and reasoning trajectories saved directly to the SQLite backend database (`react_research.db`).
