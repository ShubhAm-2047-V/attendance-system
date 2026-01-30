from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import os

app = Flask(__name__)

# ===============================
# DATABASE CONNECTION
# ===============================
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "attendance")
    )

# ===============================
# HOME / LOGIN (example)
# ===============================
@app.route("/")
def home():
    return redirect(url_for("mark_attendance"))

# ===============================
# MARK ATTENDANCE (FIXED)
# ===============================
@app.route("/mark", methods=["GET", "POST"])
def mark_attendance():
    students = []
    selected_class = ""
    selected_standard = ""

    if request.method == "POST":
        selected_class = request.form.get("class")
        selected_standard = request.form.get("standard")

        # Safety check (prevents 400 error)
        if selected_class and selected_standard:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT id, roll_no, username FROM students WHERE class = %s AND standard = %s",
                (selected_class, selected_standard)
            )

            students = cursor.fetchall()
            conn.close()

    return render_template(
        "mark_attendance.html",
        students=students,
        selected_class=selected_class,
        selected_standard=selected_standard
    )

# ===============================
# RUN APP
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
