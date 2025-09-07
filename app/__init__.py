# Create and configure the Flask app.
# - Make sure the instance exists.
# - Load default settings.
# - Register blueprints (modular groups of routes).

from flask import Flask
from pathlib import Path

def create_app():
    """
    Called by app.py to get a coonfigured Flask application.
    """
    
    app = Flask(
        __name__,
        instance_relative_config=True,  # keeps writable files in an instance outside version control
        template_folder="templates",    # where HTML templates live
        static_folder="static",         # where CSS/JS/images live
    )

    # Basic, safe defaults for local development
    app.config.from_mapping (
        SECRET_KEY="dev",
        DATABASE=str(Path(app.instance_path) / "habit_garden.sqlite3"),
    )

    # Ensure the instance exists so SQLite can create its file there
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # Register page routes
    from .routes.pages import bp as pages_bp
    app.register_blueprint(pages_bp)

    # Health-check
    @app.get("/health")
    def health():
        return {"status": "ok"}, 200
    
    return app