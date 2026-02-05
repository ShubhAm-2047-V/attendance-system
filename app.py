


CC_REPORT_CACHE = []


from flask import request

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, send_file, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# =========================
# APP SETUP
# =========================
app = Flask(__name__)
app.secret_key = "secretkey"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///attendance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

SETUP_KEY = "VERNEKAR"

# =========================
# MODELS
# =========================
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    year = db.Column(db.String(10))
    division = db.Column(db.String(5))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)

    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"))


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student = db.Column(db.String(80), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)

def get_cc_report_data():
    report_data = []

    students = (
        Attendance.query
        .with_entities(Attendance.student_name)
        .distinct()
        .all()
    )

    for (student_name,) in students:
        records = Attendance.query.filter_by(
            student_name=student_name
        ).all()

        subjects = {
            "python": None,
            "java": None,
            "mic": None,
            "es": None,
            "dcn": None,
        }

        total = 0
        count = 0

        for r in records:
            subject_key = r.subject.strip().lower()

            if subject_key in subjects:
                subjects[subject_key] = r.percentage
                total += r.percentage
                count += 1

        total_percent = round(total / count, 2) if count > 0 else 0.0

        report_data.append({
            "student": student_name,
            "python": subjects["python"],
            "java": subjects["java"],
            "mic": subjects["mic"],
            "es": subjects["es"],
            "dcn": subjects["dcn"],
            "total": total_percent
        })

    return report_data


# =========================
# INIT DB
# =========================
with app.app_context():
    db.create_all()
    for s in ["Python", "Java", "MIC", "ES", "DCN"]:
        if not Subject.query.filter_by(name=s).first():
            db.session.add(Subject(name=s))
    db.session.commit()

# =========================
# LOGIN MANAGER
# =========================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# HELPERS
# =========================
def admin_exists():
    return User.query.filter_by(role="admin").first() is not None


def generate_cc_report():
    students = User.query.filter_by(role="student").all()
    subjects = [s.name for s in Subject.query.all()]
    report = []

    for student in students:
        row = {"student": student.username}
        total_present = 0
        total_classes = 0

        for sub in subjects:
            records = Attendance.query.filter_by(
                student=student.username,
                subject=sub
            ).all()

            if records:
                present = sum(r.status == "Present" for r in records)
                percent = round((present / len(records)) * 100, 2)
                row[sub] = percent
                total_present += present
                total_classes += len(records)
            else:
                row[sub] = None

        row["total"] = round(
            (total_present / total_classes) * 100, 2
        ) if total_classes else None

        report.append(row)

    return report



def get_cc_report_data():
    report = {}

    records = Attendance.query.all()

    for att in records:
        student = (
            getattr(att, "student", None)
            or getattr(att, "username", None)
            or getattr(att, "roll_no", None)
        )

        if not student:
            continue

        if student not in report:
            report[student] = {
                "python": None,
                "java": None,
                "mic": None,
                "es": None,
                "dcn": None
            }

        subject = getattr(att, "subject", None)
        percent = getattr(att, "percentage", None)

        if subject:
            key = subject.lower()
            if key in report[student]:
                report[student][key] = percent

    final = []
    for student, subs in report.items():
        values = [v for v in subs.values() if v is not None]
        total = round(sum(values) / len(values), 2) if values else 0.0

        final.append({
            "student": student,
            "python": subs["python"],
            "java": subs["java"],
            "mic": subs["mic"],
            "es": subs["es"],
            "dcn": subs["dcn"],
            "total": total
        })

    return final

# =========================
# SETUP
# =========================
@app.route("/setup", methods=["GET", "POST"])
def setup():
    if admin_exists():
        return redirect("/")

    error = None
    if request.method == "POST":
        if request.form.get("secret_key") != SETUP_KEY:
            error = "Invalid setup key"
        else:
            admin = User(
                username="admin",
                password=generate_password_hash("admin123"),
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()
            return redirect("/")

    return render_template("setup.html", error=error)

# =========================
# LOGIN / LOGOUT
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if not admin_exists():
        return redirect("/setup")

    if request.method == "POST":
        user = User.query.filter_by(
            username=request.form.get("username")
        ).first()

        if not user or not check_password_hash(
            user.password, request.form.get("password")
        ):
            return render_template("login.html", error="Invalid credentials")

        if not user.is_active:
            return render_template("login.html", error="Account locked")

        login_user(user)

        if user.role == "admin":
            return redirect("/admin")
        if user.role == "teacher":
            return redirect("/teacher")
        if user.role == "cc":
            return redirect("/cc")
        return redirect("/student")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

# =========================
# ADMIN
# =========================
@app.route("/admin")
@login_required
def admin():
    page = request.args.get("page", 1, type=int)
    per_page = 10

    users_paginated = User.query.order_by(User.id).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return render_template(
        "admin_dashboard.html",
        users=users_paginated.items,
        pagination=users_paginated
    )

# =========================
# ADMIN ACTIONS (MISSING ROUTES)
# =========================


@app.route("/toggle_user/<int:user_id>")
@login_required
def toggle_user(user_id):
    if current_user.role != "admin":
        return redirect("/")

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot lock yourself")
        return redirect("/admin")

    user.is_active = not user.is_active
    db.session.commit()
    return redirect("/admin")


@app.route("/delete_user/<int:user_id>")
@login_required
def delete_user(user_id):
    if current_user.role != "admin":
        return redirect("/")

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot delete yourself")
        return redirect("/admin")

    db.session.delete(user)
    db.session.commit()
    return redirect("/admin")






@app.route("/add_user", methods=["GET", "POST"])
@login_required
def add_user():
    if current_user.role != "admin":
        return redirect("/")

    if request.method == "POST":
        if User.query.filter_by(username=request.form["username"]).first():
            flash("Username already exists")
            return redirect("/add_user")

        role = request.form["role"]

        user = User(
            username=request.form["username"],
            password=generate_password_hash(request.form["password"]),
            role=role,
            phone=request.form.get("phone"),
            year=request.form.get("year"),
            division=request.form.get("division"),
            subject_id=request.form.get("subject_id") if role == "teacher" else None
        )

        db.session.add(user)
        db.session.commit()
        return redirect("/admin")

    return render_template(
        "add_user.html",
        subjects=Subject.query.all()
    )

# =========================
# TEACHER
# =========================
@app.route("/teacher")
@login_required
def teacher():
    if current_user.role != "teacher":
        return redirect("/")

    today = date.today()
    records = Attendance.query.filter_by(date=today).all()

    return render_template(
        "teacher_dashboard.html",
        total_students=len(records),
        present_count=sum(r.status == "Present" for r in records),
        absent_count=sum(r.status == "Absent" for r in records)
    )

# =========================
# MARK ATTENDANCE (FIXED)
# =========================
@app.route("/mark-attendance")
@app.route("/mark_attendance")
@login_required
def mark_attendance():
    if current_user.role != "teacher":
        return redirect("/")

    year = request.args.get("year")
    division = request.args.get("division")

    if not year or not division:
        flash("Please select year and division")
        return redirect("/teacher")

    # fetch students of selected class
    users = User.query.filter_by(
        role="student",
        year=year,
        division=division
    ).all()

    # ✅ convert to JSON-safe format
    students = [
        {
            "id": u.id,
            "name": u.username
        }
        for u in users
    ]

    return render_template(
        "mark_attendance.html",
        students=students,
        year=year,
        division=division
    )


@app.route("/mark_single", methods=["POST"])
@login_required
def mark_single():
    if current_user.role != "teacher":
        return "", 403

    student = request.form["student"]
    status = request.form["status"].capitalize()
    today = date.today()
    subject_name = Subject.query.get(current_user.subject_id).name

    # ❌ prevent duplicate entry for same student + date + subject
    existing = Attendance.query.filter_by(
        student=student,
        subject=subject_name,
        date=today
    ).first()

    if existing:
        existing.status = status
    else:
        attendance = Attendance(
            student=student,
            subject=subject_name,
            status=status,
            date=today
        )
        db.session.add(attendance)

    db.session.commit()
    return "", 200

# =========================
# MONTHLY REPORT (ONLY ADD)
# =========================
  
# =========================
# CC
# =========================
@app.route("/cc")
@login_required
def cc():
    if current_user.role != "cc":
        return redirect("/")

    return render_template(
        "cc_dashboard.html",
        report=generate_cc_report()
    )
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

def clean(v):
    return "0" if v is None else str(v)

from flask import session

@app.route("/cc/report")
@login_required
def cc_report():
    global CC_REPORT_CACHE

    report_data = []

    # 🔥 PUT YOUR REAL WORKING LOGIC HERE 🔥
    # (this example matches your screenshot)

    students = [
        ("student1", 100.0, 100.0, None, None, None, 100.0),
        ("student2", 100.0, 100.0, None, None, None, 100.0),
        ("student3", 100.0, 100.0, None, None, None, 100.0),
        ("student4", 100.0, 100.0, None, None, None, 100.0),
        ("student5", 100.0, 100.0, None, None, None, 100.0),
    ]

    for s in students:
        report_data.append({
            "student": s[0],
            "python": s[1],
            "java": s[2],
            "mic": s[3],
            "es": s[4],
            "dcn": s[5],
            "total": s[6],
        })

    # 🔴 THIS LINE IS THE MOST IMPORTANT LINE 🔴
    CC_REPORT_CACHE = report_data

    print("CC_REPORT_CACHE SET:", CC_REPORT_CACHE)  # DEBUG

    return render_template(
        "cc_report.html",
        report_data=report_data
    )
@app.route("/cc/export-pdf")
@login_required
def export_cc_pdf():
    from flask import send_file
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    import io

    report_data = get_cc_report_data()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph("<b>Full Student Attendance Report</b>", styles["Title"])
    )
    elements.append(Paragraph("<br/>", styles["Normal"]))

    table_data = [[
        "Student", "Python", "Java", "MIC", "ES", "DCN", "Total %"
    ]]

    for r in report_data:
        table_data.append([
            r["student"],
            r["python"] if r["python"] is not None else "—",
            r["java"] if r["java"] is not None else "—",
            r["mic"] if r["mic"] is not None else "—",
            r["es"] if r["es"] is not None else "—",
            r["dcn"] if r["dcn"] is not None else "—",
            r["total"]
        ])

    table = Table(table_data, colWidths=[90, 60, 60, 60, 60, 60, 60])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="attendance_report.pdf",
        mimetype="application/pdf"
    )




# =========================
# STUDENT
# =========================
@app.route("/student")
@login_required
def student():
    if current_user.role != "student":
        return redirect("/")

    records = Attendance.query.filter_by(
        student=current_user.username
    ).order_by(Attendance.date.desc()).all()

    streak = 0
    for r in records:
        if r.status == "Present":
            streak += 1
        else:
            break

    return render_template(
        "student_dashboard.html",
        records=records,
        present_count=sum(r.status == "Present" for r in records),
        absent_count=sum(r.status == "Absent" for r in records),
        streak=streak
    )

# =========================
# MONTHLY REPORT (TEACHER)
# =========================
@app.route("/monthly_chart")
@login_required
def monthly_chart():
    if current_user.role != "teacher":
        return redirect("/")

    year = request.args.get("year")
    division = request.args.get("division")

    if not year or not division:
        flash("Please select year and division")
        return redirect("/teacher")

    subject_name = Subject.query.get(current_user.subject_id).name

    students = User.query.filter_by(
        role="student",
        year=year,
        division=division
    ).all()

    report = []
    total_percent = 0
    count = 0

    for s in students:
        records = Attendance.query.filter_by(
            student=s.username,
            subject=subject_name
        ).order_by(Attendance.date).all()

        present = sum(r.status == "Present" for r in records)
        absent = sum(r.status == "Absent" for r in records)
        total = len(records)
        percent = round((present / total) * 100, 2) if total else 0

        if total:
            total_percent += percent
            count += 1

        report.append({
            "student": s.username,
            "present": present,
            "absent": absent,
            "total": total,
            "percentage": percent,
            "records": records
        })

    class_average = round(total_percent / count, 2) if count else 0

    return render_template(
        "monthly_chart.html",
        report=report,
        subject=subject_name,
        class_average=class_average
    )


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
