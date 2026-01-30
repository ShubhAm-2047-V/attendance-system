from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import date
import os

app = Flask(__name__)
app.secret_key = "attendance_secret_key"

DB_NAME = "attendance.db"

def get_db():
    return sqlite3.connect(DB_NAME)

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

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users VALUES (NULL,'admin','admin123','Admin')")
        cur.execute("INSERT INTO users VALUES (NULL,'teacher1','1234','Teacher')")
        cur.execute("INSERT INTO users VALUES (NULL,'student1','1234','Student')")

    conn.commit()
    conn.close()

create_tables()

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        r = request.form["role"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=? AND role=?",
            (u, p, r)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            session["role"] = r
            return redirect("/admin" if r=="Admin" else "/teacher" if r=="Teacher" else "/student")
        else:
            error = "Invalid login"

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

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
        today = date.today().isoformat()
        conn = get_db()
        cur = conn.cursor()

        for s in ["Rahul", "Aman"]:
            cur.execute(
                "INSERT INTO attendance VALUES (NULL,?,?,?,?)",
                (s, request.form["subject"], request.form[s], today)
            )

        conn.commit()
        conn.close()
        return redirect("/teacher")

    return render_template("mark_attendance.html")

@app.route("/monthly_chart")
def monthly_chart():
    if session.get("role") != "Teacher":
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT subject,
               COUNT(*) total,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) present
        FROM attendance GROUP BY subject
    """)
    data = cur.fetchall()
    conn.close()

    subjects = [d[0] for d in data]
    percentages = [(d[2]/d[1])*100 for d in data]

    return render_template(
        "monthly_chart.html",
        subjects=subjects,
        percentages=percentages
    )

@app.route("/student")
def student_dashboard():
    if session.get("role") != "Student":
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT subject,
               COUNT(*) total,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) present
        FROM attendance GROUP BY subject
    """)
    data = cur.fetchall()
    conn.close()
    return render_template("student_dashboard.html", data=data)

if __name__ == "__main__":
    app.run()
