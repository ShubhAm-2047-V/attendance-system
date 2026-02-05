from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Attendance, User

api_cc = Blueprint("api_cc", __name__)

@api_cc.route("/api/cc/report", methods=["GET"])
@jwt_required()
def cc_report():
    user = get_jwt_identity()

    if user["role"] != "cc":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    students = User.query.filter_by(role="student").all()
    report = []

    for s in students:
        records = Attendance.query.filter_by(student=s.username).all()
        present = sum(r.status == "Present" for r in records)
        total = len(records)

        report.append({
            "student": s.username,
            "present": present,
            "total": total,
            "percentage": round((present / total) * 100, 2) if total else 0
        })

    return jsonify({"status": "success", "report": report})
