from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from models import db, User

# ✅ THIS IS WHAT app.py IS TRYING TO IMPORT
auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "Username and password required"
        }), 400

    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404

    if not check_password_hash(user.password, password):
        return jsonify({
            "status": "error",
            "message": "Invalid password"
        }), 401

    return jsonify({
        "status": "success",
        "username": user.username,
        "role": user.role
    })
