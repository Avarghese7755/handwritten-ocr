"""
FILE       : app.py
PROJECT    : Handwritten OCR | Capstone Project 2025
PROGRAMMER : Bhuwan Shrestha (8892146), Alen Varghese (8827755), 
             Shubh Soni (8887735), Dev Patel (8866936)
DATE       : 2025-03-11
DESCRIPTION:
This is the main application file for the Handwritten OCR Flask web application.
It initializes the app, handles authentication (email/password ),
user session tracking, text extraction via Google Vision API, text translation, 
file download in multiple formats, feedback submission, and route registration. 
It also creates all necessary tables for application setup and deployment.
"""
from flask import Flask, request, render_template, redirect, url_for, send_file, jsonify, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import os
from db import get_db_connection

import secrets
import uuid
import datetime
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from vision_api import extract_text
from translate_api import translate_text

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from oauthlib.oauth2 import WebApplicationClient
from whitenoise import WhiteNoise


#  base directory for the app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

# Add whitenoise for serving static files in production

app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/')
app.wsgi_app.add_files('static/', prefix='static/')

#  environment variables for production, fall back to defaults
app.secret_key = os.environ.get("SECRET_KEY", "secret_key")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["LOGS_FOLDER"] = os.path.join(BASE_DIR, "user_logs")

# Create logs directory if it doesn't exist
if not os.path.exists(app.config["LOGS_FOLDER"]):
    os.makedirs(app.config["LOGS_FOLDER"])

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])


# FUNCTION   : log_user_activity
# DESCRIPTION: Logs a user activity with timestamp to a file named after the user ID.
# PARAMETERS : user_id (int), activity (str), details (str, optional)
# RETURNS    : None

def log_user_activity(user_id, activity, details=None):
    """Log user activity to a file"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file = os.path.join(app.config["LOGS_FOLDER"], f"{user_id}_log.txt")
        
        with open(log_file, "a") as f:
            log_entry = f"{timestamp} - {activity}"
            if details:
                log_entry += f" - {details}"
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"Error logging activity: {e}")

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = ""


# Email configuration from environment variables
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "handwrittensender@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "ymribhdrhrbsymls")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT", "handwrittenocr448@gmail.com")

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# FUNCTION   : upload_file
# DESCRIPTION: Handles image upload, extracts text using OCR, saves results to DB
# PARAMETERS : None (uses request and current_user)
# RETURNS    : Rendered template (index.html or result.html)

@app.route("/", methods=["GET", "POST"])
@login_required
def upload_file():
    if request.method == "POST":
        if "files" not in request.files:
            return "No files uploaded!"

        files = request.files.getlist("files")
        results = []
        conn = get_db_connection()
        c = conn.cursor()
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                extracted_text = extract_text(filepath)
                formatted_text = ' '.join(extracted_text.split()).replace('. ', '. ')
                results.append({"image": filename, "text": formatted_text})
                c.execute("INSERT INTO history (user_id, image, text) VALUES (%s, %s, %s)",
                          (current_user.id, filename, formatted_text))
                
                # Log this activity
                log_user_activity(current_user.id, "OCR Performed", f"File: {filename}")
        conn.commit()
        conn.close()
        return render_template("result.html", results=results)
    return render_template("index.html")

# FUNCTION   : translate
# DESCRIPTION: Translates given text to a selected language using translation API
# PARAMETERS : text (str), language (str) from form
# RETURNS    : Translated text (str)

@app.route("/translate", methods=["POST"])
@login_required
def translate():
    text = request.form.get("text")
    target_lang = request.form.get("language")
    translated_text = translate_text(text, target_lang)
    
    # Log this activity
    log_user_activity(current_user.id, "Translation", f"Language: {target_lang}")
    
    return translated_text

# FUNCTION   : download
# DESCRIPTION: Generates and downloads extracted text as .txt, .pdf, or .docx.
# PARAMETERS : text, filename, format (from form)
# RETURNS    : send_file response with downloadable file

@app.route("/download", methods=["POST"])
@login_required
def download():
    text = request.form["text"]
    filename = request.form["filename"]
    format = request.form["format"]
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], f"{filename}.{format}")
    text = text.replace('<br>', '\n').replace('</p><p>', '\n').replace('<p>', '').replace('</p>', '\n')
    if format == "docx":
        doc = Document()
        doc.add_paragraph(text)
        doc.save(filepath)
    elif format == "pdf":
        pdf = SimpleDocTemplate(filepath, pagesize=letter)
        pdf.build([Paragraph(text)])
    else:  # txt
        with open(filepath, "w", encoding='utf-8') as f:
            f.write(text)
    
    # Log this activity
    log_user_activity(current_user.id, "File Downloaded", f"Format: {format}, Filename: {filename}")
    
    return send_file(filepath, as_attachment=True)

# FUNCTION   : feedback
# DESCRIPTION: Sends feedback message via email from contact form
# PARAMETERS : name, email, message (from JSON)
# RETURNS    : JSON object with success status and message

@app.route("/feedback", methods=["POST"])
def feedback():
    # Get the form data
    name = request.json.get("name")
    email = request.json.get("email")
    message = request.json.get("message")
    
    success = True
    error_message = ""
    email_sent = False
    
    #  send email
    try:
        # Email credentials - Using secondary email to send to primary email
        secondary_email = "handwrittensender@gmail.com"  # Secondary email address
        secondary_app_password = "ymribhdrhrbsymls"  # App password without spaces (ymri bhdr hrbs ymls)
        recipient_email = "handwrittenocr448@gmail.com"  # Primary email that will receive
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = secondary_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Contact Form: Message from {name}"
        msg['Reply-To'] = email  # Set reply-to as the user's email
        
        # Email body
        body = f"""
        New message from contact form:
        
        Name: {name}
        Email: {email}
        
        Message:
        {message}
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server using SSL instead of STARTTLS
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            # Login with secondary email credentials
            server.login(secondary_email, secondary_app_password)
            server.send_message(msg)
            
            email_sent = True
            print(f"Email sent successfully from {secondary_email} to {recipient_email}")
            
        # Log this activity if user is logged in
        if current_user.is_authenticated:
            log_user_activity(current_user.id, "Contact Form Submitted", f"Email: {email}")
            
    except smtplib.SMTPAuthenticationError as auth_err:
        print(f"SMTP Authentication Error: {auth_err}")
        print("This means the app password or email is incorrect")
        success = False
        error_message = "Failed to send your message. Authentication error"
        
    except smtplib.SMTPException as smtp_err:
        print(f"SMTP Error: {smtp_err}")
        print("This is a general SMTP error")
        success = False
        error_message = "Failed to send your message. SMTP error"
        
    except ConnectionRefusedError as conn_err:
        print(f"Connection Refused: {conn_err}")
        print("This typically means a firewall or network issue is blocking the connection")
        success = False
        error_message = "Failed to send your message. Connection refused."
        
    except TimeoutError as timeout_err:
        print(f"Connection Timeout: {timeout_err}")
        print("The connection to the Gmail server timed out.")
        success = False
        error_message = "Failed to send your message. Connection timeout."
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        success = False
        error_message = "Failed to send your message. Please try again later"
    
    return jsonify({
        "success": success, 
        "email_sent": email_sent,
        "message": "Thank you! Your message has been sent." if success else error_message
    })

# FUNCTION   : login
# DESCRIPTION: Authenticates user via username/email and password and  Logs session
# PARAMETERS : username, password (from form)
# RETURNS    : Redirect to dashboard or login page with error

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_or_email = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        c = conn.cursor()
        
        # Check if the input matches either username or email
        c.execute("SELECT id FROM users WHERE (username=%s OR gmail=%s) AND password=%s", 
                 (username_or_email, username_or_email, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            login_user(User(user[0]))
            
            # Log this activity
            log_user_activity(user[0], "Login", f"IP: {request.remote_addr}")
            
            # Record this session
            session_id = uuid.uuid4().hex
            session['_id'] = session_id
            
            # Get IP address and user agent
            ip_address = request.remote_addr
            user_agent = request.user_agent.string
            
            # Create session record in database
            conn = get_db_connection()
            c = conn.cursor()
            
            # Create table if not exists
            c.execute('''CREATE TABLE IF NOT EXISTS user_sessions 
                      (id INTEGER PRIMARY KEY, user_id INTEGER, session_id TEXT, 
                       ip_address TEXT, device_info TEXT, last_active DATETIME)''')
            
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Insert new session
            c.execute('''INSERT INTO user_sessions (user_id, session_id, ip_address, device_info, last_active) 
                       VALUES (%s, %s, %s, %s, %s)''', 
                     (user[0], session_id, ip_address, user_agent, current_time))
            
            conn.commit()
            conn.close()
            
            return redirect(url_for("upload_file"))
        return render_template("login.html", error="Invalid credentials!")
    return render_template("login.html")

# FUNCTION   : signup
# DESCRIPTION: Registers new user, saves to DB, logs activity, and redirects to login
# PARAMETERS : username, password, gmail 
# RETURNS    : Redirect to login page or show error

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        gmail = request.form["gmail"]

        try:
            conn = get_db_connection()
            c = conn.cursor()

            # Use RETURNING id to get the new user ID
            c.execute("""
                INSERT INTO users (username, password, gmail)
                VALUES (%s, %s, %s) RETURNING id
            """, (username, password, gmail))

            user_id = c.fetchone()[0]  # Grab the returned ID
            conn.commit()
            conn.close()

            # Log this activity
            log_user_activity(user_id, "Account Created", f"Username: {username}, Email: {gmail}")

            flash("Account created successfully! Please login with your credentials.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            flash(f"Error: {e}", "danger")
            return render_template("signup.html")

    return render_template("signup.html")

# FUNCTION   : logout
# DESCRIPTION: Logs out the current user, deletes their session record, and redirects to login
# PARAMETERS : None (uses current_user and session)
# RETURNS    : Redirect to login page

@app.route("/logout")
@login_required
def logout():
    # Log this activity
    log_user_activity(current_user.id, "Logout", f"IP: {request.remote_addr}")
    
    # Remove session record from database
    session_id = session.get('_id')
    if session_id:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Delete this session
        c.execute("DELETE FROM user_sessions WHERE user_id=%s AND session_id=%s", 
                 (current_user.id, session_id))
        
        conn.commit()
        conn.close()
    
    logout_user()
    return redirect(url_for("login"))

# Import additional routes from app_helper
from app_helper import *

# Initialize database tables if they don't exist
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create users table if not exists
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        gmail TEXT UNIQUE NOT NULL
    )
    ''')
    
    # Create history table if not exists
    c.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        image TEXT NOT NULL,
        text TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create user_sessions table if not exists
    c.execute('''
    CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        ip_address TEXT,
        device_info TEXT,
        last_active DATETIME
    )
    ''')
    
    # Create user_preferences table if not exists
    c.execute('''
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INTEGER PRIMARY KEY,
        analytics INTEGER DEFAULT 0,
        notifications INTEGER DEFAULT 0,
        language TEXT DEFAULT 'en'
    )
    ''')
    
    # Create user_2fa table if not exists
    c.execute('''
    CREATE TABLE IF NOT EXISTS user_2fa (
        user_id INTEGER PRIMARY KEY,
        enabled INTEGER DEFAULT 0,
        secret TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print("Database initialized successfully")

if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Get port from environment variable or default to 8080
    port = int(os.environ.get("PORT", 8080))
   
    app.run(host="0.0.0.0", port=port, debug=False)