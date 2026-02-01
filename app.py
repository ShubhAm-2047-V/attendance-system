from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import smtplib
from email.message import EmailMessage

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

EMAIL_ADDRESS = "dvernekar59@gmail.com"
EMAIL_PASSWORD = "&hubh@ngi"

# =========================
# MODELS
# =========================
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    year = db.Column(db.String(10))
    division = db.Column(db.String(5))
    phone = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)

    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"))


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student = db.Column(db.String(80), nullable=False)
    subject = db.Column(db.String(50), nullable=False)  # ✅ NEW
    status = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)


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


# =========================
# SETUP
# =========================
@app.route("/setup", methods=["GET", "POST"])
def setup():
    if admin_exists():
        return redirect("/")

    error = None
    if request.method == "POST":
        if request.form.get("secret_key", "").strip() != SETUP_KEY:
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
    if current_user.role != "admin":
        return redirect("/")
    return render_template(
        "admin_dashboard.html",
        users=User.query.all()
    )


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


@app.route("/toggle_user/<int:user_id>")
@login_required
def toggle_user(user_id):
    if current_user.role != "admin":
        return redirect("/")

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    return redirect("/admin")


@app.route("/delete_user/<int:user_id>")
@login_required
def delete_user(user_id):
    if current_user.role != "admin":
        return redirect("/")

    db.session.delete(User.query.get_or_404(user_id))
    db.session.commit()
    return redirect("/admin")


# =========================
# TEACHER
# =========================
@app.route("/teacher")
@login_required
def teacher():
    if current_user.role != "teacher":
        return redirect("/")
    return render_template("teacher_dashboard.html")


@app.route("/mark_attendance")
@login_required
def mark_attendance():
    if current_user.role != "teacher":
        return redirect("/")

    students = User.query.filter_by(
        role="student",
        year=request.args.get("year"),
        division=request.args.get("division")
    ).all()

    return render_template("mark_attendance.html", students=students)


@app.route("/mark_single", methods=["POST"])
@login_required
def mark_single():
    if current_user.role != "teacher":
        return "", 403

    student = request.form.get("student")
    status = request.form.get("status")
    subject = Subject.query.get(current_user.subject_id)

    if not student or not status or not subject:
        return "", 400

    attendance = Attendance(
        student=student,
        subject=subject.name,   # ✅ subject saved
        status=status.capitalize(),
        date=date.today()
    )

    db.session.add(attendance)
    db.session.commit()
    return "", 200


@app.route("/monthly_chart")
@login_required
def monthly_chart():
    if current_user.role != "teacher":
        return redirect("/")

    year = request.args.get("year")
    division = request.args.get("division")

    if not year or not division:
        return redirect("/teacher")

    students = User.query.filter_by(
        role="student",
        year=year,
        division=division
    ).all()

    names = [s.username for s in students]

    records = Attendance.query.filter(
        Attendance.student.in_(names)
    ).order_by(Attendance.date).all()

    present_count = sum(r.status == "Present" for r in records)
    absent_count = sum(r.status == "Absent" for r in records)

    return render_template(
        "monthly_chart.html",
        records=records,
        present_count=present_count,
        absent_count=absent_count,
        year=year,
        division=division
    )


# =========================
# CC
# =========================
@app.route("/cc")
@login_required
def cc():
    if current_user.role != "cc":
        return redirect("/")

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
                row[sub] = f"{percent}%"
                total_present += present
                total_classes += len(records)
            else:
                row[sub] = "—"

        row["total"] = (
            f"{round((total_present / total_classes) * 100, 2)}%"
            if total_classes else "—"
        )

        report.append(row)

    return render_template(
        "cc_dashboard.html",
        report=report,
        subjects=subjects
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

    present_count = sum(r.status == "Present" for r in records)
    absent_count = sum(r.status == "Absent" for r in records)

    streak = 0
    for r in records:
        if r.status == "Present":
            streak += 1
        else:
            break

    return render_template(
        "student_dashboard.html",
        records=records,
        present_count=present_count,
        absent_count=absent_count,
        streak=streak
    )


# =========================
# RUN
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        for s in ["Python", "Java", "MIC", "ES", "DCN"]:
            if not Subject.query.filter_by(name=s).first():
                db.session.add(Subject(name=s))
        db.session.commit()

    app.run(debug=True)
