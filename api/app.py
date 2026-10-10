"""FreshTrack api: the only component that talks to the database."""

import logging
import os

import psycopg
from flask import Flask, jsonify

log = logging.getLogger(__name__)


def database_is_reachable(database_url):
    """Return True if we can open a connection and run a trivial query."""
    if not database_url:
        log.warning("DATABASE_URL is not set")
        return False
    try:
        with psycopg.connect(database_url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error as exc:
        # Log the reason for operators, but never send it to the caller.
        log.warning("Database check failed: %s", exc.__class__.__name__)
        return False


def create_app():
    app = Flask(__name__)
    app.config["DATABASE_URL"] = os.environ.get("DATABASE_URL", "")

    @app.get("/health")
    def health():
        # Liveness: the process is running and can answer. No database check here,
        # otherwise a database outage would make Kubernetes restart healthy api Pods.
        return jsonify(status="ok"), 200

    @app.get("/ready")
    def ready():
        # Readiness: only accept traffic when the database is reachable.
        if database_is_reachable(app.config["DATABASE_URL"]):
            return jsonify(status="ready"), 200
        return jsonify(status="not ready"), 503

    return app
