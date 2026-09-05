from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

app = Flask(__name__)

# Secret key
app.secret_key = os.getenv("SECRET_KEY")

# Admin credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# PostgreSQL connection
DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            date_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Unread'
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


@app.route("/")
def home():
    return render_template("index.html")


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

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO messages
        (name, email, message, date_time, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            name,
            email,
            message,
            date_time,
            "Unread"
        )
    )

    conn.commit()
    cursor.close()
    conn.close()

    return "Message received and saved successfully!"


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            app.secret_key
            and ADMIN_USERNAME
            and ADMIN_PASSWORD
            and username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):
            session["admin_logged_in"] = True
            return redirect("/admin")

        return "Invalid username or password!"

    return render_template("login.html")


@app.route("/admin")
def admin():

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            message,
            date_time,
            status
        FROM messages
        ORDER BY id DESC
    """)

    messages = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(*) FROM messages"
    )

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

    cursor.close()
    conn.close()

    return render_template(
        "admin.html",
        messages=messages,
        total_messages=total_messages,
        unread_messages=unread_messages,
        read_messages=read_messages
    )


@app.route(
    "/mark-read/<int:message_id>",
    methods=["POST"]
)
def mark_read(message_id):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE messages
        SET status = 'Read'
        WHERE id = %s
        """,
        (message_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/admin")


@app.route(
    "/mark-unread/<int:message_id>",
    methods=["POST"]
)
def mark_unread(message_id):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE messages
        SET status = 'Unread'
        WHERE id = %s
        """,
        (message_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/admin")


@app.route(
    "/delete/<int:message_id>",
    methods=["POST"]
)
def delete_message(message_id):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM messages
        WHERE id = %s
        """,
        (message_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/admin")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# Initialize PostgreSQL database
init_db()


if __name__ == "__main__":
    app.run(debug=True)