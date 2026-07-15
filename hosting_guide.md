# Hosting Guide: Render (Backend) + Netlify (Frontend)

This guide provides step-by-step instructions for hosting the **ReAct Academic Research Assistant** using **Render** for the backend database/reasoning engine, and **Netlify** for the frontend user interface.

---

## Part 1: Deploying the Backend on Render
Render will host the Python/Flask API service. Because SQLite and ChromaDB write data to the local disk, we must configure a **Persistent Disk Volume** so your database records and semantic paper chunks are not wiped on service restarts.

### Step 1: Create a Render Web Service
1. Sign in to your [Render Dashboard](https://dashboard.render.com/) and click **New > Web Service**.
2. Connect your Git repository.
3. Configure the following parameters:
   - **Name**: `react-research-backend` (or a name of your choice)
   - **Region**: Select the region closest to you
   - **Branch**: `main`
   - **Root Directory**: `backend` *(Crucial: This tells Render to compile only the backend directory)*
   - **Runtime**: `Python`

### Step 2: Configure Build & Start Commands
Scroll down to the commands section:
- **Build Command**: 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  gunicorn --workers 1 --threads 8 --timeout 0 --bind 0.0.0.0:$PORT app:app
  ```
  *(Note: Gunicorn needs the `--threads` flag to handle concurrent Server-Sent Events reasoning streams without blocking).*

### Step 3: Add a Persistent Disk Volume
To prevent SQLite (`react_research.db`) and ChromaDB vector indices from resetting on every redeploy:
1. Go to the **Disk** tab in the web service menu.
2. Click **Add Disk**.
3. Configure the disk settings:
   - **Name**: `sqlite-chroma-data`
   - **Mount Path**: `/var/data`
   - **Size**: `1 GB` to `5 GB` (Plenty for thousands of paper chunks and query logs)

### Step 4: Add Environment Variables
Go to the **Environment** tab and add the following variables:
- `API_KEY`: *(Your primary LLM API key)*
- `BASE_URL`: *(Leave blank to default to standard OpenAI, or set to your custom endpoint)*
- `MODEL_NAME`: `auto`
- `SQLITE_DB_PATH`: `/var/data/react_research.db` *(Points SQLite database to the persistent disk)*
- `CHROMA_PERSIST_DIR`: `/var/data/chroma` *(Points ChromaDB collection to the persistent disk)*
- `PDF_STORAGE_DIR`: `/var/data/pdfs` *(Points downloaded PDFs folder to the persistent disk)*
- `FLASK_ENV`: `production`

Click **Save Changes** and deploy the service. Once deployed, copy the generated service URL (e.g., `https://react-research-backend.onrender.com`).

---

## Part 2: Deploying the Frontend on Netlify
Netlify will host the static compiled React single-page application and route calls to your Render API endpoint.

### Step 1: Create a Netlify Site
1. Log in to the [Netlify Dashboard](https://app.netlify.com/) and click **Add new site > Import an existing project**.
2. Connect your Git repository.
3. Configure the site settings:
   - **Base directory**: `frontend` *(Crucial: Tells Netlify to look inside the frontend folder)*
   - **Build command**: `npm run build`
   - **Publish directory**: `dist`
   - **Node Version**: `18` or higher (standard Netlify default)

### Step 2: Configure the API Endpoint URL
We must tell Netlify where to send requests.
1. In the Netlify setup screen, click **Add environment variables** (or go to **Site Configuration > Environment Variables** after creation).
2. Create a new variable:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: `https://your-app.onrender.com/api` (Replace this with the actual URL of the Render backend web service you created in Part 1, making sure to append `/api` at the end).

### Step 3: Configure URL Rewrites for Single Page App Routing
To prevent Netlify from returning 404 errors when refreshing the page:
1. Create a file named `_redirects` inside your project's `frontend/public/` directory (if it doesn't already exist).
2. Add the following redirect rule inside `_redirects`:
   ```text
   /*    /index.html   200
   ```
   *(This ensures Netlify redirects all router paths back to the main index.html file so the React app handles it).*

Deploy the site. Your Automated Academic Research Assistant is now hosted in production!
