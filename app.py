from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
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

SETUP_KEY = "shubham"

EMAIL_ADDRESS = "dvernekar59@gmail.com"
EMAIL_PASSWORD = "&hubh@ngi"

# =========================
# MODELS
# =========================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    year = db.Column(db.String(10))
    division = db.Column(db.String(5))
    phone = db.Column(db.String(100))

    is_active = db.Column(db.Boolean, default=True)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.Date, default=date.today)
    is_read = db.Column(db.Boolean, default=False)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
with app.app_context():
    db.create_all()



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


def send_absent_email(to_email, student, teacher):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Attendance Alert"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg.set_content(
            f"You were marked ABSENT today by {teacher}."
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

    except Exception as e:
        print("Email failed:", e)


# =========================
# FIRST RUN SETUP
# =========================
@app.route("/setup", methods=["GET", "POST"])
def setup():
    if admin_exists():
        return redirect("/")

    if request.method == "POST":
        key = request.form.get("key")
        if key != SETUP_KEY:
            return render_template("setup.html", error="Invalid setup key")

        admin = User(
            username="admin",
            password="admin123",
            role="admin",
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        return redirect("/")

    return render_template("setup.html")


# =========================
# LOGIN
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if not admin_exists():
        return redirect("/setup")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username, password=password).first()

        if not user:
            return render_template("login.html", error="Invalid credentials")

        if not user.is_active:
            return render_template("login.html", error="Account is locked")

        login_user(user)

        if user.role == "admin":
            return redirect("/admin")
        elif user.role == "teacher":
            return redirect("/teacher")
        else:
            return redirect("/student")

    return render_template("login.html")


# =========================
# LOGOUT
# =========================
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
    users = User.query.all()
    return render_template("admin_dashboard.html", users=users)


@app.route("/add_user", methods=["GET", "POST"])
@login_required
def add_user():
    if current_user.role != "admin":
        return redirect("/")

    if request.method == "POST":
        user = User(
            username=request.form.get("username"),
            password=request.form.get("password"),
            role=request.form.get("role"),
            year=request.form.get("year"),
            division=request.form.get("division"),
            phone=request.form.get("phone"),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/admin")

    return render_template("add_user.html")


@app.route("/delete_user/<int:user_id>")
@login_required
def delete_user(user_id):
    if current_user.role != "admin":
        return redirect("/")

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return redirect("/admin")

    if user.role == "admin":
        if User.query.filter_by(role="admin").count() <= 1:
            return redirect("/admin")

    db.session.delete(user)
    db.session.commit()
    return redirect("/admin")


@app.route("/toggle_user/<int:user_id>")
@login_required
def toggle_user(user_id):
    if current_user.role != "admin":
        return redirect("/")

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return redirect("/admin")

    if user.role == "admin":
        if User.query.filter_by(role="admin", is_active=True).count() <= 1:
            return redirect("/admin")

    user.is_active = not user.is_active
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


@app.route("/select_class", methods=["GET", "POST"])
@login_required
def select_class():
    if current_user.role != "teacher":
        return redirect("/")

    next_url = request.args.get("next")

    if request.method == "POST":
        year = request.form.get("year")
        division = request.form.get("division")
        return redirect(f"{next_url}?year={year}&division={division}")

    return render_template("select_class.html", next_url=next_url)


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
    student_name = request.form.get("student")
    status = request.form.get("status").capitalize()

    db.session.add(
        Attendance(student=student_name, status=status, date=date.today())
    )
    db.session.commit()

    if status == "Absent":
        student = User.query.filter_by(username=student_name).first()
        if student:
            db.session.add(
                Notification(
                    user_id=student.id,
                    message=f"You were marked ABSENT today by {current_user.username}"
                )
            )
            db.session.commit()

            if student.phone:
                send_absent_email(student.phone, student.username, current_user.username)

    return "OK"


@app.route("/monthly_chart")
@login_required
def monthly_chart():
    if current_user.role != "teacher":
        return redirect("/")

    students = User.query.filter_by(
        role="student",
        year=request.args.get("year"),
        division=request.args.get("division")
    ).all()

    names = [s.username for s in students]

    records = Attendance.query.filter(
        Attendance.student.in_(names)
    ).all()

    present = sum(1 for r in records if r.status.lower() == "present")
    absent = sum(1 for r in records if r.status.lower() == "absent")

    return render_template(
        "monthly_chart.html",
        records=records,
        present_count=present,
        absent_count=absent
    )


# =========================
# STUDENT  ✅ FIXED HERE
# =========================
@app.route("/student")
@login_required
def student():
    if current_user.role != "student":
        return redirect("/")

    records = Attendance.query.filter_by(
        student=current_user.username
    ).order_by(Attendance.date.desc()).all()

    present_count = sum(1 for r in records if r.status.lower() == "present")
    absent_count = sum(1 for r in records if r.status.lower() == "absent")

    streak = 0
    for r in records:
        if r.status.lower() == "present":
            streak += 1
        else:
            break

    # ✅ ONLY TODAY’S NOTIFICATIONS
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        created_at=date.today()
    ).order_by(Notification.id.desc()).all()

    return render_template(
    "student_dashboard.html",
    records=records,
    present_count=present_count,
    absent_count=absent_count,
    streak=streak,
    notifications=notifications,
    today=date.today()   # ✅ ADD THIS
)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
