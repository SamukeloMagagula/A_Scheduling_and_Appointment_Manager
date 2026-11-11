"""Flask application factory. Run with:
    python app.py
or:
    flask --app app.py run --debug

The static front-end pages (index.html etc.) sit one directory up and are
served as-is at the root, so the whole site runs under one process.
"""
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from sqlalchemy.exc import SQLAlchemyError

from auth import load_current_user
from config import Config


def create_app() -> Flask:
    front_dir = Path(__file__).resolve().parent.parent  # project root with index.html
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    # Stash the current user onto flask.g at the start of every request.
    app.before_request(load_current_user)

    # Blueprints
    from blueprints.entries    import bp as entries_bp
    from blueprints.users      import bp as users_bp
    from blueprints.teams      import bp as teams_bp
    from blueprints.department import bp as department_bp
    from blueprints.timesheet  import bp as timesheet_bp
    from blueprints.customers  import bp as customers_bp
    from blueprints.projects   import bp as projects_bp
    from blueprints.logs       import bp as logs_bp
    for bp in (entries_bp, users_bp, teams_bp, department_bp,
               timesheet_bp, customers_bp, projects_bp, logs_bp):
        app.register_blueprint(bp)

    # Serve the existing static site from the project root.
    @app.get("/")
    def home():
        return send_from_directory(front_dir, "index.html")

    @app.get("/<path:filename>")
    def static_passthrough(filename: str):
        # Only serve files that actually exist; let Flask 404 otherwise.
        target = front_dir / filename
        if target.is_file():
            return send_from_directory(front_dir, filename)
        return jsonify(error="not found"), 404

    # Uniform JSON errors for the API; HTML pages keep Flask's default.
    @app.errorhandler(SQLAlchemyError)
    def _db_error(err):  # pragma: no cover - diagnostic only
        return jsonify(error="database error", detail=str(err.__class__.__name__)), 500

    @app.errorhandler(404)
    def _not_found(_):
        return jsonify(error="not found"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
