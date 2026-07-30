"""Dashboard entry point for JobHunter-AI."""

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def home():
    return jsonify({
        "application": "JobHunter-AI",
        "status": "running",
        "message": "Dashboard initialized"
    })


@app.get("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
