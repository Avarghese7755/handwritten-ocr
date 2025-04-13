"""
FILE       : app_helper.py
PROJECT    : Handwritten OCR | Capstone Project 2025
PROGRAMMER : Bhuwan Shrestha (8892146), Alen Varghese (8827755), 
             Shubh Soni (8887735), Dev Patel (8866936)
DATE       : 2025-03-10
DESCRIPTION:
This file defines additional Flask routes to handle extended user functionality 
including history viewing, session management, profile updates, 2FA, preferences, 
language settings, and feedback submission. It also logs each user activity 
to help administrators monitor engagement and system usage
"""


from flask import request, render_template, redirect, url_for, send_file, jsonify, session, flash
from flask_login import login_required, current_user
import os
import uuid
import datetime
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from db import get_db_connection
import secrets
from app import app, log_user_activity

# FUNCTION   : history
# DESCRIPTION: Retrieves and displays the user's image processing history from 
#              the database, ordered by most recent
# PARAMETERS : None (uses current_user from Flask-Login)
# RETURNS    : Rendered 'history.html' page with a list of historical records

@app.route("/history")
@login_required
def history():
    # Log this activity
    log_user_activity(current_user.id, "Viewed History")
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT image, text, timestamp FROM history WHERE user_id=%s ORDER BY timestamp DESC",
              (current_user.id,))
    records = c.fetchall()
    conn.close()
    return render_template("history.html", records=records)


# FUNCTION   : clear_history
# DESCRIPTION: Deletes all text/image processing history records of the current user
# PARAMETERS : None (uses current_user from Flask-Login)
# RETURNS    : Redirects to the 'history' page

@app.route("/clear_history", methods=["POST"])
@login_required
def clear_history():
    # Log this activity
    log_user_activity(current_user.id, "Cleared History")
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM history WHERE user_id=%s", (current_user.id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for("history"))


# FUNCTION   : search_history
# DESCRIPTION: Searches user history records based on a text or timestamp query
# PARAMETERS : query (from request.args)
# RETURNS    : Rendered 'history.html' with search result records

@app.route("/search_history", methods=["GET"])
@login_required
def search_history():
    # Get search query
    query = request.args.get("query", "")
    
    # Log this activity
    log_user_activity(current_user.id, "Searched History", f"Query: {query}")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Search in text and timestamp 
    c.execute("""
        SELECT image, text, timestamp FROM history 
        WHERE user_id=%s AND (text LIKE %s OR timestamp LIKE %s) 
        ORDER BY timestamp DESC
    """, (current_user.id, f"%{query}%", f"%{query}%"))
    
    records = c.fetchall()
    conn.close()
    
    return render_template("history.html", records=records)

# FUNCTION   : download_history
# DESCRIPTION: Creates a downloadable text file for a selected history entry
# PARAMETERS : filename (from form), text (from form)
# RETURNS    : Flask send_file response to download .txt file

@app.route("/download_history", methods=["POST"])
@login_required
def download_history():
    # Get form data
    filename = request.form.get("filename", "unknown")
    text = request.form.get("text", "")
    
    # Create a text file to download
    text_content = text.replace('<br>', '\n').replace('</p><p>', '\n').replace('<p>', '').replace('</p>', '\n')
    
    # Log this activity
    log_user_activity(current_user.id, "Downloaded History Record", f"Text from image: {filename}")
    
    # Create file in memory
    file_io = io.BytesIO(text_content.encode('utf-8'))
    file_io.seek(0)
    
    return send_file(
        file_io,
        mimetype='text/plain',
        as_attachment=True,
        download_name=f"history_{filename}.txt"
    )

# FUNCTION   : update_profile
# DESCRIPTION: Allows the user to update their profile details (username, email, password)
# PARAMETERS : username, email, password (from form)
# RETURNS    : Redirects to the settings page with a success flash message

@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Log what's being changed
    changes = []
    if username:
        changes.append("username")
    if email:
        changes.append("email")
    if password:
        changes.append("password")
    
    log_user_activity(current_user.id, "Profile Update", f"Changed: {', '.join(changes)}")
    
    # Only update fields that were provided
    if username and email and password:
        c.execute("UPDATE users SET username=%s, gmail=%s, password=%s WHERE id=%s", 
                 (username, email, password, current_user.id))
    elif username and email:
        c.execute("UPDATE users SET username=%s, gmail=%s WHERE id=%s", 
                 (username, email, current_user.id))
    elif username and password:
        c.execute("UPDATE users SET username=%s, password=%s WHERE id=%s", 
                 (username, password, current_user.id))
    elif email and password:
        c.execute("UPDATE users SET gmail=%s, password=%s WHERE id=%s", 
                 (email, password, current_user.id))
    elif username:
        c.execute("UPDATE users SET username=%s WHERE id=%s", 
                 (username, current_user.id))
    elif email:
        c.execute("UPDATE users SET gmail=%s WHERE id=%s", 
                 (email, current_user.id))
    elif password:
        c.execute("UPDATE users SET password=%s WHERE id=%s", 
                 (password, current_user.id))
    
    conn.commit()
    conn.close()
    
    # Flash a success message
    flash("Profile updated successfully", "success")
    return redirect(url_for("settings"))

# FUNCTION   : toggle_2fa
# DESCRIPTION: Enables or disables 2-Factor Authentication for the current user
# PARAMETERS : enabled (from JSON body)
# RETURNS    : JSON object with success status and updated 2FA state

@app.route("/toggle_2fa", methods=["POST"])
@login_required
def toggle_2fa():
    enabled = request.json.get("enabled", False)
    
    # Log this activity
    log_user_activity(current_user.id, "2FA Setting Changed", f"Enabled: {enabled}")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_2fa 
                (user_id INTEGER PRIMARY KEY, enabled INTEGER, secret TEXT)''')
    
    
    c.execute("SELECT * FROM user_2fa WHERE user_id=%s", (current_user.id,))
    record = c.fetchone()
    
    if record:
        # Update existing record
        c.execute("UPDATE user_2fa SET enabled=%s WHERE user_id=%s", 
                 (1 if enabled else 0, current_user.id))
    else:
       
        secret = secrets.token_hex(16)
        c.execute("INSERT INTO user_2fa (user_id, enabled, secret) VALUES (%s, %s, %s)",
                 (current_user.id, 1 if enabled else 0, secret))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "enabled": enabled})


# FUNCTION   : toggle_analytics
# DESCRIPTION: Toggles the analytics preference for the current user
# PARAMETERS : enabled (from JSON body)
# RETURNS    : JSON object with success status and analytics state 

@app.route("/toggle_analytics", methods=["POST"])
@login_required
def toggle_analytics():
    enabled = request.json.get("enabled", False)
    
    # Log this activity
    log_user_activity(current_user.id, "Analytics Setting Changed", f"Enabled: {enabled}")
    
    conn = get_db_connection()
    c = conn.cursor()
    
 
    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences 
                (user_id INTEGER PRIMARY KEY, analytics INTEGER, notifications INTEGER, language TEXT)''')
    
    
    c.execute("SELECT * FROM user_preferences WHERE user_id=%s", (current_user.id,))
    record = c.fetchone()
    
    if record:
     
        c.execute("UPDATE user_preferences SET analytics=%s WHERE user_id=%s", 
                 (1 if enabled else 0, current_user.id))
    else:
     
        c.execute("INSERT INTO user_preferences (user_id, analytics, notifications, language) VALUES (%s, %s, %s, %s)",
                 (current_user.id, 1 if enabled else 0, 0, "en"))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "enabled": enabled})

# FUNCTION   : toggle_notifications
# DESCRIPTION: Enables or disables notification preference for the user
# PARAMETERS : enabled (from JSON body)
# RETURNS    : JSON object with success status and notification state

@app.route("/toggle_notifications", methods=["POST"])
@login_required
def toggle_notifications():
    enabled = request.json.get("enabled", False)
    
    # Log this activity
    log_user_activity(current_user.id, "Notifications Setting Changed", f"Enabled: {enabled}")
    
    conn = get_db_connection()
    c = conn.cursor()
    
   
    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences 
                (user_id INTEGER PRIMARY KEY, analytics INTEGER, notifications INTEGER, language TEXT)''')
    
 
    c.execute("SELECT * FROM user_preferences WHERE user_id=%s", (current_user.id,))
    record = c.fetchone()
    
    if record:
      
        c.execute("UPDATE user_preferences SET notifications=%s WHERE user_id=%s", 
                 (1 if enabled else 0, current_user.id))
    else:
       
        c.execute("INSERT INTO user_preferences (user_id, analytics, notifications, language) VALUES (%s, %s, %s, %s)",
                 (current_user.id, 0, 1 if enabled else 0, "en"))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "enabled": enabled})

# FUNCTION   : update_language
# DESCRIPTION: Updates the preferred interface language of the user
# PARAMETERS : language (from JSON body)
# RETURNS    : JSON object with success status and new language

@app.route("/update_language", methods=["POST"])
@login_required
def update_language():
    language = request.json.get("language", "en")
    
    # Log this activity
    log_user_activity(current_user.id, "Language Setting Changed", f"Language: {language}")
    
    conn = get_db_connection()
    c = conn.cursor()
   
    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences 
                (user_id INTEGER PRIMARY KEY, analytics INTEGER, notifications INTEGER, language TEXT)''')
    

    c.execute("SELECT * FROM user_preferences WHERE user_id=%s", (current_user.id,))
    record = c.fetchone()
    
    if record:
     
        c.execute("UPDATE user_preferences SET language=%s WHERE user_id=%s", 
                 (language, current_user.id))
    else:
  
        c.execute("INSERT INTO user_preferences (user_id, analytics, notifications, language) VALUES (%s, %s, %s, %s)",
                 (current_user.id, 0, 0, language))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "language": language})

# FUNCTION   : get_active_sessions
# DESCRIPTION: Retrieves all currently active sessions for the user
# PARAMETERS : None
# RETURNS    : JSON object with session list and success flag

@app.route("/get_active_sessions", methods=["GET"])
@login_required
def get_active_sessions():
    # Log this activity
    log_user_activity(current_user.id, "Viewed Active Sessions")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create sessions table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS user_sessions 
                (id INTEGER PRIMARY KEY, user_id INTEGER, session_id TEXT, 
                 ip_address TEXT, device_info TEXT, last_active DATETIME)''')
    
    # Get all active sessions for the user
    c.execute("SELECT id, session_id, ip_address, device_info, last_active FROM user_sessions WHERE user_id=%s",
             (current_user.id,))
    sessions = c.fetchall()
    
    conn.close()
    
    session_list = []
    for s in sessions:
        session_list.append({
            "id": s[0],
            "session_id": s[1],
            "ip_address": s[2],
            "device_info": s[3],
            "last_active": s[4]
        })
    
    return jsonify({"success": True, "sessions": session_list})

# FUNCTION   : terminate_session
# DESCRIPTION: Terminates a selected session after verifying user ownership
# PARAMETERS : session_id (from URL parameter)
# RETURNS    : JSON object indicating if session termination was successful
 
@app.route("/terminate_session/<int:session_id>", methods=["POST"])
@login_required
def terminate_session(session_id):
    # Log this activity
    log_user_activity(current_user.id, "Terminated Session", f"Session ID: {session_id}")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Verify this session belongs to the current user before deleting
    c.execute("SELECT user_id FROM user_sessions WHERE id=%s", (session_id,))
    session_record = c.fetchone()
    
    if session_record and int(session_record[0]) == current_user.id:
        c.execute("DELETE FROM user_sessions WHERE id=%s", (session_id,))
        conn.commit()
        success = True
    else:
        success = False
    
    conn.close()
    
    return jsonify({"success": success})


# FUNCTION   : settings
# DESCRIPTION: Displays the user settings page, allows updating of settings such as
#              2FA, analytics, notifications, and language, while also logging the session
# PARAMETERS : GET or POST request
# RETURNS    : Rendered 'settings.html' with user settings and status

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    # Log this activity
    log_user_activity(current_user.id, "Viewed Settings Page")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get user info
    c.execute("SELECT username, gmail FROM users WHERE id=%s", (current_user.id,))
    user = c.fetchone()
    
    # Get user preferences
    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences 
                (user_id INTEGER PRIMARY KEY, analytics INTEGER, notifications INTEGER, language TEXT)''')
    
    c.execute("SELECT analytics, notifications, language FROM user_preferences WHERE user_id=%s", 
             (current_user.id,))
    pref = c.fetchone()
    
    if not pref:
        # Create default preferences if none exist
        c.execute("INSERT INTO user_preferences (user_id, analytics, notifications, language) VALUES (%s, %s, %s, %s)",
                 (current_user.id, 0, 0, "en"))
        conn.commit()
        analytics_enabled = False
        notifications_enabled = False
        language = "en"
    else:
        analytics_enabled = bool(pref[0])
        notifications_enabled = bool(pref[1])
        language = pref[2]
    
    # Get 2FA status
    c.execute('''CREATE TABLE IF NOT EXISTS user_2fa 
                (user_id INTEGER PRIMARY KEY, enabled INTEGER, secret TEXT)''')
    
    c.execute("SELECT enabled FROM user_2fa WHERE user_id=%s", (current_user.id,))
    twofa = c.fetchone()
    twofa_enabled = bool(twofa[0]) if twofa else False
    
    # Record this session 
    session_id = session.get('_id', uuid.uuid4().hex)
    session['_id'] = session_id
    
    # Get IP address and user agent
    ip_address = request.remote_addr
    user_agent = request.user_agent.string
    
    # Create or update session record
    c.execute('''CREATE TABLE IF NOT EXISTS user_sessions 
                (id INTEGER PRIMARY KEY, user_id INTEGER, session_id TEXT, 
                 ip_address TEXT, device_info TEXT, last_active DATETIME)''')
    
   
    c.execute("SELECT id FROM user_sessions WHERE user_id=%s AND session_id=%s", 
             (current_user.id, session_id))
    existing_session = c.fetchone()
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if existing_session:
        # Update last active time
        c.execute("UPDATE user_sessions SET last_active=%s WHERE id=%s", 
                 (current_time, existing_session[0]))
    else:
        # Create new session record
        c.execute('''INSERT INTO user_sessions (user_id, session_id, ip_address, device_info, last_active) 
                   VALUES (%s, %s, %s, %s, %s)''', 
                 (current_user.id, session_id, ip_address, user_agent, current_time))
    
    conn.commit()
    conn.close()
    
    return render_template("settings.html", 
                          username=user[0], 
                          gmail=user[1],
                          twofa_enabled=twofa_enabled,
                          analytics_enabled=analytics_enabled,
                          notifications_enabled=notifications_enabled,
                          language=language)

# FUNCTION   : about
# DESCRIPTION: Renders the About page and logs the activity if user is authenticated
# PARAMETERS : None
# RETURNS    : Rendered 'about.html' page

@app.route("/about")
def about():
    # Only log if user is logged in
    if current_user.is_authenticated:
        log_user_activity(current_user.id, "Viewed About Page")
        
    team_members = [
        {"name": "Bhuwan Shrestha", "role": "Lead Developer", "image": "bhuwan_shrestha.jpg"},
        {"name": "Alen Varghese", "role": "UI/UX Designer", "image": "alen_varghese.jpg"},
        {"name": "Shubh Soni", "role": "Machine Learning Expert", "image": "shubh_soni.jpg"},
        {"name": "Dev Patel", "role": "Backend Engineer", "image": "dev_patel.jpg"}
    ]
    return render_template("about.html", team_members=team_members)

# FUNCTION   : contact
# DESCRIPTION: Renders the Contact page and logs the activity if user is authenticated
# PARAMETERS : None
# RETURNS    : Rendered 'contact.html' page

@app.route("/contact")
def contact():
    # Only log if user is logged in
    if current_user.is_authenticated:
        log_user_activity(current_user.id, "Viewed Contact Page")
        
    return render_template("contact.html")


# FUNCTION   : references
# DESCRIPTION: Renders the References page and logs the activity if user is authenticated
# PARAMETERS : None
# RETURNS    : Rendered 'references.html' page

@app.route("/references")
def references():
    # Only log if user is logged in
    if current_user.is_authenticated:
        log_user_activity(current_user.id, "Viewed References Page")
        
    return render_template("references.html")

# FUNCTION   : download_activity_log
# DESCRIPTION: Lets the user download their activity log file. If not available, it creates one
# PARAMETERS : None
# RETURNS    : send_file response with the user's activity log 

@app.route("/download_activity_log")
@login_required
def download_activity_log():
    log_file = os.path.join(app.config["LOGS_FOLDER"], f"{current_user.id}_log.txt")
    
    # Log this activity
    log_user_activity(current_user.id, "Activity Log Downloaded")
    
    # Check if log file exists
    if os.path.exists(log_file):
        return send_file(log_file, as_attachment=True, 
                         download_name=f"activity_log_{current_user.id}.txt")
    else:
        # Create empty file with header if it doesn't exist
        with open(log_file, "w") as f:
            f.write(f"Activity log for user ID: {current_user.id}\n")
            f.write("==============================================\n\n")
        return send_file(log_file, as_attachment=True, 
                         download_name=f"activity_log_{current_user.id}.txt")


# FUNCTION   : submit_rating
# DESCRIPTION: Handles rating form submission, logs the activity, and optionally sends an email.
# PARAMETERS : rating, comment (from JSON body)
# RETURNS    : JSON object with success flag and status of email delivery

@app.route("/submit_rating", methods=["POST"])
@login_required
def submit_rating():
    # Get the rating data
    rating_data = request.json
    rating = rating_data.get("rating")
    comment = rating_data.get("comment", "")
    
    success = True
    error_message = ""
    email_sent = False
    
    # Get user information
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT username, gmail FROM users WHERE id=%s", (current_user.id,))
    user = c.fetchone()
    conn.close()
    
    username = user[0] if user else "Unknown"
    user_email = user[1] if user else "Unknown"
    
    # Try to send email notification
    try:
        # Email credentials
        secondary_email = "handwrittensender@gmail.com"  # Secondary email address
        secondary_app_password = "ymribhdrhrbsymls"  # App password 
        recipient_email = "handwrittenocr448@gmail.com"  # Primary email to receive notifications
        
        # Email body
        body = f"""
New rating submission:

Username: {username}
Email: {user_email}
Rating: {rating}/5 stars

Additional Comment:
{comment}
"""
        #  yagmail to send the email
        try:
            import yagmail
            # Configure yagmail
            yag = yagmail.SMTP(secondary_email, secondary_app_password)
            # Send email
            yag.send(
                to=recipient_email,
                subject=f"Rating Notification: {username} rated {rating}/5 stars",
                contents=body,
                headers={'Reply-To': user_email}
            )
            email_sent = True
            print(f"Rating notification email sent successfully from {secondary_email} to {recipient_email}")
        except ImportError:
            print("Yagmail not available, falling back to smtplib")
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = secondary_email
            msg['To'] = recipient_email
            msg['Subject'] = f"Rating Notification: {username} rated {rating}/5 stars"
            msg['Reply-To'] = user_email  # Set reply-to as the user's email
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                # Login with secondary email credentials
                server.login(secondary_email, secondary_app_password)
                server.send_message(msg)
                
                email_sent = True
                print(f"Rating notification email sent successfully from {secondary_email} to {recipient_email}")
            
        # Log this activity
        log_user_activity(current_user.id, "Rating Submitted", f"Rating: {rating}/5 stars")
            
    except Exception as e:
        print(f"Error sending rating notification email: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        # Still return success even if email fails
    
    return jsonify({
        "success": success, 
        "email_sent": email_sent,
        "message": "Thank you for your rating!" if success else error_message
    })