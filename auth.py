"""
FILE       : auth.py
PROJECT    : Handwritten OCR | Capstone Project 2025
PROGRAMMER : Bhuwan Shrestha (8892146), Alen Varghese (8827755),
             Shubh Soni (8887735), Dev Patel (8866936)
DATE       : 2025-03-16
DESCRIPTION:
This module handles authentication for the Handwritten OCR web application,
including user signup, login, logout, session tracking, and email verification
"""

from flask import Blueprint, request, render_template, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from db import get_db_connection
import bcrypt
import random
import uuid
import datetime
import os
from smtplib import SMTP_SSL
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()
auth = Blueprint('auth', __name__)

login_manager = LoginManager()
login_manager.login_view = "auth.login"

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


# FUNCTION   : load_user
# DESCRIPTION: Loads a user from the database using the user ID (used by Flask-Login)
# PARAMETERS : user_id (int)
# RETURNS    : User object or None

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
    user = c.fetchone()
    conn.close()
    return User(user[0], user[1]) if user else None

# FUNCTION   : login
# DESCRIPTION: Authenticates a user if credentials are valid and email is verified.
# PARAMETERS : username/password from form
# RETURNS    : Redirect to upload page or render login with error

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT id, username, password FROM users WHERE (username = %s OR gmail = %s) AND verified = TRUE",
            (username_or_email, username_or_email)
        )
        user = c.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            user_obj = User(user[0], user[1])
            login_user(user_obj)

            session_id = uuid.uuid4().hex
            session['_id'] = session_id

            ip_address = request.remote_addr
            user_agent = request.user_agent.string
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            c.execute('''CREATE TABLE IF NOT EXISTS user_sessions 
                         (id SERIAL PRIMARY KEY, user_id INTEGER, session_id TEXT, 
                          ip_address TEXT, device_info TEXT, last_active TIMESTAMP)''')

            c.execute('''INSERT INTO user_sessions (user_id, session_id, ip_address, device_info, last_active)
                         VALUES (%s, %s, %s, %s, %s)''',
                      (user[0], session_id, ip_address, user_agent, now))
            conn.commit()
            conn.close()
            return redirect(url_for('upload_file'))
        conn.close()
        return render_template('login.html', error='Invalid credentials or Gmail not verified!')
    return render_template('login.html')

# FUNCTION   : signup
# DESCRIPTION: Registers a new user, hashes their password, sends verification code
# PARAMETERS : username, password, gmail from form
# RETURNS    : Redirect to verification page or render signup with error

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        gmail = request.form['gmail']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, gmail, verified) VALUES (%s, %s, %s, FALSE)",
                      (username, hashed_password, gmail))
            conn.commit()
        except Exception as e:
            conn.rollback()
            conn.close()
            return render_template('signup.html', error='Username or Gmail already exists!')

        verification_code = str(random.randint(1000, 9999))
        session['verification_code'] = verification_code
        session['username'] = username
        
        conn.close()
        return redirect(url_for('auth.verify'))
    return render_template('signup.html')

# FUNCTION   : logout
# DESCRIPTION: Logs out the current user and deletes their active session record
# PARAMETERS : None
# RETURNS    : Redirect to login page

@auth.route('/logout')
@login_required
def logout():
    session_id = session.get('_id')
    conn = get_db_connection()
    c = conn.cursor()
    if session_id:
        c.execute("DELETE FROM user_sessions WHERE user_id = %s AND session_id = %s",
                  (current_user.id, session_id))
    conn.commit()
    conn.close()
    logout_user()
    return redirect(url_for('auth.login'))

