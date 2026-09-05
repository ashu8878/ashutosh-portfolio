from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)

app.secret_key = "my_secret_key_123"


# =========================
# DATABASE
# =========================

def init_db():

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            date_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Unread'
        )
    """)

    # Old database compatibility
    columns = [column[1] for column in cursor.execute(
        "PRAGMA table_info(messages)"
    ).fetchall()]

    if "date_time" not in columns:
        cursor.execute(
            "ALTER TABLE messages ADD COLUMN date_time TEXT"
        )

        cursor.execute(
            "UPDATE messages SET date_time = ? WHERE date_time IS NULL",
            (datetime.now().strftime("%d-%m-%Y %I:%M %p"),)
        )

    if "status" not in columns:
        cursor.execute(
            "ALTER TABLE messages ADD COLUMN status TEXT DEFAULT 'Unread'"
        )

        cursor.execute(
            "UPDATE messages SET status = 'Unread' WHERE status IS NULL"
        )

    conn.commit()
    conn.close()


# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template("index.html")


# =========================
# CONTACT FORM
# =========================

@app.route("/contact", methods=["POST"])
def contact():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email or not message:
        return "Please fill all fields."

    date_time = datetime.now().strftime(
        "%d-%m-%Y %I:%M %p"
    )

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO messages
        (name, email, message, date_time, status)
        VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        email,
        message,
        date_time,
        "Unread"
    ))

    conn.commit()
    conn.close()

    return "Message received and saved successfully!"


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == "admin" and password == "1234":

            session["admin_logged_in"] = True

            return redirect("/admin")

        return "Invalid username or password!"

    return render_template("login.html")


# =========================
# ADMIN DASHBOARD
# =========================

@app.route("/admin")
def admin():

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email, message, date_time, status
        FROM messages
        ORDER BY id DESC
    """)

    messages = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*)
        FROM messages
    """)

    total_messages = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM messages
        WHERE status = 'Unread'
    """)

    unread_messages = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM messages
        WHERE status = 'Read'
    """)

    read_messages = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        messages=messages,
        total_messages=total_messages,
        unread_messages=unread_messages,
        read_messages=read_messages
    )


# =========================
# MARK AS READ
# =========================

@app.route("/mark-read/<int:message_id>", methods=["POST"])
def mark_read(message_id):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE messages
        SET status = 'Read'
        WHERE id = ?
    """, (message_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")


# =========================
# MARK AS UNREAD
# =========================

@app.route("/mark-unread/<int:message_id>", methods=["POST"])
def mark_unread(message_id):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE messages
        SET status = 'Unread'
        WHERE id = ?
    """, (message_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")


# =========================
# DELETE MESSAGE
# =========================

@app.route("/delete/<int:message_id>", methods=["POST"])
def delete_message(message_id):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM messages
        WHERE id = ?
    """, (message_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)