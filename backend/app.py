import os
from flask import Flask, jsonify
from flask_cors import CORS
from config import PORT
from database.db import init_sqlite_db
from database.vector_store import get_or_create_collection
from react.sse import sse_bp

def create_app():
    app = Flask(__name__)
    
    # Configure Flask-CORS to allow frontend origins (default Vite port 5173, etc.)
    CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]}})

    # Register Blueprint
    app.register_blueprint(sse_bp)

    @app.cli.command("init-db")
    def init_db_command():
        """Flask CLI command (`flask init-db`) to initialize SQLite and ChromaDB."""
        init_sqlite_db()
        get_or_create_collection("research_papers")
        print("Successfully initialized SQLite database schema and ChromaDB vector collection via `flask init-db`.")

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "ok",
            "service": "ReAct Automated Academic Research Assistant API",
            "version": "1.0.0"
        })

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", PORT))
    print(f"[*] Starting ReAct Research Assistant Flask Server on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
