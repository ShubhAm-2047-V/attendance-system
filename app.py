from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import date

app = Flask(__name__)

# ---------- SESSION CONFIG (RENDER SAFE) ----------
app.secret_key = "ATTENDANCE_SYSTEM_SECRET_2026"
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True
)

# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect("attendance.db")

def create_tables():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        subject TEXT,
        status TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

create_tables()

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        # HARD ADMIN LOGIN (SAFE FOR RENDER)
        if username == "admin" and password == "admin123" and role == "Admin":
            session.clear()
            session["role"] = "Admin"
            return redirect("/admin")

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=? AND role=?",
            (username, password, role)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            session.clear()
            session["role"] = role
            if role == "Teacher":
                return redirect("/teacher")
            elif role == "Student":
                return redirect("/student")
        else:
            error = "Invalid login details"

    return render_template("login.html", error=error)

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- ADMIN DASHBOARD ----------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "Admin":
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, role FROM users")
    users = cur.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", users=users)

# ---------- ADD USER ----------
@app.route("/add_user", methods=["GET", "POST"])
def add_user():
    if session.get("role") != "Admin":
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?,?,?)",
            (username, password, role)
        )
        conn.commit()
        conn.close()

        return redirect("/admin")

    return render_template("add_user.html")

# ---------- DELETE USER ----------
@app.route("/delete_user/<username>")
def delete_user(username):
    if session.get("role") != "Admin":
        return redirect("/")

    # Prevent deleting main admin
    if username == "admin":
        return redirect("/admin")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()

    return redirect("/admin")

# ---------- TEACHER ----------
@app.route("/teacher")
def teacher_dashboard():
    if session.get("role") != "Teacher":
        return redirect("/")
    return render_template("teacher_dashboard.html")

@app.route("/mark", methods=["GET", "POST"])
def mark_attendance():
    if session.get("role") != "Teacher":
        return redirect("/")

    if request.method == "POST":
        subject = request.form["subject"]
        today = date.today().isoformat()

        conn = get_db()
        cur = conn.cursor()

        for student in ["Rahul", "Aman"]:
            cur.execute(
                "INSERT INTO attendance (student_name, subject, status, date) VALUES (?,?,?,?)",
                (student, subject, request.form[student], today)
            )

        conn.commit()
        conn.close()
        return redirect("/teacher")

    return render_template("mark_attendance.html")

# ---------- STUDENT ----------
@app.route("/student")
def student_dashboard():
    if session.get("role") != "Student":
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT subject,
               COUNT(*) AS total,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present
        FROM attendance
        GROUP BY subject
    """)
    data = cur.fetchall()
    conn.close()

    return render_template("student_dashboard.html", data=data)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run()
