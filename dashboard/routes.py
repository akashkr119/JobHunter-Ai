"""Dashboard route definitions."""

from flask import Blueprint, jsonify

bp = Blueprint("dashboard", __name__)


@bp.get("/jobs")
def jobs():
    return jsonify({"message": "Jobs endpoint", "items": []})


@bp.get("/matches")
def matches():
    return jsonify({"message": "Top matches endpoint", "items": []})


@bp.get("/crawler/status")
def crawler_status():
    return jsonify({"status": "idle"})


@bp.post("/crawler/run")
def run_crawler():
    return jsonify({"message": "Crawler trigger placeholder"})
