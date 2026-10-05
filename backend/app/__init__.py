import os
from dotenv import load_dotenv

# Load backend/.env before importing Config or provider-dependent modules.
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=env_path, override=False)

from flask import Flask, jsonify
from flask_cors import CORS
from .config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    provider_name = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()
    print(f"[DEVGUARD CONFIG] Configured LLM_PROVIDER={provider_name}")

    CORS(app)

    from .main import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error=str(e.description)), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error=str(e.description)), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify(error="Internal server error"), 500

    return app
