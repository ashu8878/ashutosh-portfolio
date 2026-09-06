from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import re
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv
import psycopg2

from werkzeug.security import check_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


load_dotenv()


app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
DATABASE_URL = os.getenv("DATABASE_URL")


# =====================================================
# SECURITY SETTINGS
# =====================================================

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("RENDER") == "true"
)


# =====================================================
# SECURITY HEADERS
# =====================================================

@app.after_request
def add_security_headers(response):

    response.headers["X-Content-Type-Options"] = "nosniff"

    response.headers["X-Frame-Options"] = "SAMEORIGIN"

    response.headers["Referrer-Policy"] = (
        "strict-origin-when-cross-origin"
    )

    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "font-src 'self' https: data:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'self'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    return response


# =====================================================
# CSRF PROTECTION
# =====================================================

csrf = CSRFProtect(app)


# =====================================================
# LOGIN RATE LIMITING
# =====================================================

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[]
)


# =====================================================
# DATABASE
# =====================================================

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


# =====================================================
# HOME
# =====================================================

@app.route("/")
def home():

    return render_template("index.html")


# =====================================================
# CONTACT
# =====================================================

@app.route("/contact", methods=["POST"])
def contact():

    name = request.form.get("name", "").strip()

    email = request.form.get("email", "").strip()

    message = request.form.get("message", "").strip()


    # -------------------------------------------------
    # INPUT LENGTH LIMITS
    # -------------------------------------------------

    if len(name) > 100:

        return "Name is too long."


    if len(email) > 254:

        return "Email is too long."


    if len(message) > 5000:

        return "Message is too long."


    # -------------------------------------------------
    # REQUIRED FIELDS
    # -------------------------------------------------

    if not name or not email or not message:

        return "Please fill all fields."


    # -------------------------------------------------
    # NAME VALIDATION
    # -------------------------------------------------

    if not re.fullmatch(
        r"[A-Za-zÀ-ÿ .'-]+",
        name
    ):

        return "Please enter a valid name."


    # -------------------------------------------------
    # EMAIL VALIDATION
    # -------------------------------------------------

    if not re.fullmatch(
        r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
        r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$",
        email
    ):

        return "Please enter a valid email address."


    # -------------------------------------------------
    # MESSAGE VALIDATION
    # -------------------------------------------------

    if len(message) < 2:

        return "Message is too short."


    # -------------------------------------------------
    # DATE & TIME
    # -------------------------------------------------

    date_time = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d-%m-%Y %I:%M %p")


    # -------------------------------------------------
    # DATABASE INSERT
    # -------------------------------------------------

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

    # -------------------------------------------------
    # EMAIL NOTIFICATION
    # -------------------------------------------------

    try:
        mail_server = os.getenv("MAIL_SERVER")
        mail_port = int(os.getenv("MAIL_PORT", "587"))
        mail_username = os.getenv("MAIL_USERNAME")
        mail_password = os.getenv("MAIL_PASSWORD")
        mail_to = os.getenv("MAIL_TO", "ashutosh.code.in@gmail.com")

        if all([mail_server, mail_username, mail_password, mail_to]):

            email_msg = EmailMessage()

            email_msg["Subject"] = "New Portfolio Contact Message"
            email_msg["From"] = mail_username
            email_msg["To"] = mail_to

            email_msg.set_content(
                f"""You received a new message through your portfolio website.

Name: {name}
Email: {email}

Message:
{message}

Date & Time: {date_time}
"""
            )

            with smtplib.SMTP(mail_server, mail_port) as smtp:
                smtp.starttls()
                smtp.login(mail_username, mail_password)
                smtp.send_message(email_msg)

    except Exception as email_error:
        print("Email notification failed:", email_error)

    return "Message received and saved successfully!"


# =====================================================
# LOGIN
# =====================================================

@app.route("/login", methods=["GET", "POST"])
@limiter.limit(
    "5 per minute",
    methods=["POST"]
)
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
            and ADMIN_PASSWORD_HASH
            and username == ADMIN_USERNAME
            and check_password_hash(
                ADMIN_PASSWORD_HASH,
                password
            )
        ):

            session["admin_logged_in"] = True

            return redirect("/admin")


        return "Invalid username or password!"


    return render_template("login.html")


# =====================================================
# ADMIN
# =====================================================

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


# =====================================================
# MARK READ
# =====================================================

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


# =====================================================
# MARK UNREAD
# =====================================================

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


# =====================================================
# DELETE MESSAGE
# =====================================================

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


# =====================================================
# LOGOUT
# =====================================================

@app.route(
    "/logout",
    methods=["POST"]
)
def logout():

    session.clear()

    return redirect("/login")


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

init_db()


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    app.run(debug=True)