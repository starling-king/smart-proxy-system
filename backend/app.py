import logging
from pathlib import Path
from flask import Flask, send_from_directory
from flask_cors import CORS

# Import blueprints
from api.auth import auth_bp
from api.dashboard import dashboard_bp
from api.claims import claims_bp
from api.timetable import timetable_bp

def create_app():
    # --- 1. SETUP LOGGING ---
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # --- 2. DEFINE PATHS (Using Pathlib for robustness) ---
    # Current file is in /backend/app.py (or similar), we resolve to absolute path
    backend_dir = Path(__file__).parent.resolve()
    # Frontend is sibling to backend folder
    frontend_dir = backend_dir.parent / 'frontend'

    if not frontend_dir.exists():
        logger.warning(f"Frontend directory not found at: {frontend_dir}")

    # --- 3. INITIALIZE FLASK ---
    app = Flask(__name__, static_folder=str(frontend_dir), static_url_path='')

    # Enable CORS (Allow all origins for now, can be restricted for prod)
    CORS(app)
    app.config["JSON_SORT_KEYS"] = False

    # --- 4. REGISTER BLUEPRINTS ---
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api")
    app.register_blueprint(claims_bp, url_prefix="/api")
    app.register_blueprint(timetable_bp, url_prefix="/api")

    # --- 5. SERVE FRONTEND ---
    @app.route('/')
    def serve_frontend():
        return send_from_directory(frontend_dir, 'index.html')

    # Fallback for SPA routing (optional but recommended for React/Vue apps)
    @app.errorhandler(404)
    def not_found(e):
        return send_from_directory(frontend_dir, 'index.html')

    return app

if __name__ == "__main__":
    app = create_app()
    print("----------------------------------------------------------------")
    print("SYSTEM READY: Open your browser and go to http://localhost:5000")
    print("----------------------------------------------------------------")
    
    # HOST="0.0.0.0" IS REQUIRED FOR DOCKER
    app.run(debug=False, host="0.0.0.0", port=5000)