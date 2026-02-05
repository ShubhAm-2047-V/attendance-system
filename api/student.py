from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Attendance

api_student = Blueprint("api_student", __name__)

@api_student.route("/api/student/dashboard", methods=["GET"])
@jwt_required()
def student_dashboard():
    user = get_jwt_identity()

    if user["role"] != "student":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    records = Attendance.query.filter_by(student=user["username"]).all()

    present = sum(r.status == "Present" for r in records)
    absent = sum(r.status == "Absent" for r in records)

    streak = 0
    for r in sorted(records, key=lambda x: x.date, reverse=True):
        if r.status == "Present":
            streak += 1
        else:
            break

    return jsonify({
        "status": "success",
        "username": user["username"],
        "present_days": present,
        "absent_days": absent,
        "streak": streak,
        "records": [
            {
                "subject": r.subject,
                "status": r.status,
                "date": r.date.isoformat()
            } for r in records
        ]
    })
