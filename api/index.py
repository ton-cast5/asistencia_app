from flask import Flask, jsonify, request
from database import get_db
from datetime import datetime

app = Flask(__name__)

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "time": datetime.now().isoformat()
    })

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    return jsonify({
        "success": True,
        "message": "API funciona en Vercel"
    })
