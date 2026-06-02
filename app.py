from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import jwt
import datetime
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import logging


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  


TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER')
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        from twilio.rest import Client
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except Exception:
        logging.exception('Twilio client not available')

SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 0)) if os.environ.get('SMTP_PORT') else None
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
SMTP_FROM = os.environ.get('SMTP_FROM')

import smtplib
from email.message import EmailMessage


app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
USER_DATA_FILE = os.environ.get('USER_DATA_FILE', 'users.json')


pending_signups = {}
pending_logins = {}


def load_users():
    if not os.path.exists(USER_DATA_FILE):
        return {}

    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
            users = json.load(file)
    except (json.JSONDecodeError, OSError):
        logging.exception('Failed to load users JSON file')
        return {}

    return users if isinstance(users, dict) else {}


def save_user(username, password, email, dateofbirth, phone, registered_at):
    users = load_users()
    users[username] = {
        'password': password,
        'email': email,
        'dateofbirth': dateofbirth,
        'phone': phone,
        'registered_at': registered_at
    }

    with open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(users, file, indent=4)


def get_all_users():
    users = load_users()
    return [
        {
            "username": username,
            "email": user.get("email"),
            "dateofbirth": user.get("dateofbirth"),
            "phone": user.get("phone"),
            "registered_at": user.get("registered_at")
        }
        for username, user in users.items()
    ]


def send_otp_via_twilio(phone, otp):
    """Send OTP via Twilio SMS. Returns True on success, False otherwise."""
    if not twilio_client or not TWILIO_FROM_NUMBER:
        return False
    try:
        message = twilio_client.messages.create(
            body=f"Your verification code is: {otp}",
            from_=TWILIO_FROM_NUMBER,
            to=phone
        )
        return True
    except Exception:
        logging.exception('Failed to send OTP via Twilio')
        return False


def send_otp_via_email(to_email, otp):
    """Send OTP via SMTP email. Returns True on success, False otherwise."""
    if not (SMTP_HOST and SMTP_PORT and SMTP_FROM):
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Your verification code'
        msg['From'] = SMTP_FROM
        msg['To'] = to_email
        msg.set_content(f'Your verification code is: {otp}')

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASS:
                server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception:
        logging.exception('Failed to send OTP via email')
        return False


def parse_json_request():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


def get_bearer_token():
    auth_header = request.headers.get('Authorization', '')
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    return parts[1]


@app.route("/")
def index():
    """Render the login page."""
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    """Render the user dashboard (requires authentication)."""
    return render_template("dashboard.html")

@app.route("/profile")
def profile_page():
    """Render the profile page."""
    return render_template("profile.html")

@app.route("/education")
def education_page():
    """Render the educational resources page."""
    return render_template("education.html")

@app.route("/games")
def games_page():
    """Render the game library page."""
    return render_template("games.html")

@app.route("/github")
def github_page():
    """Render the GitHub page."""
    return render_template("github.html")

@app.route("/linkedin")
def linkedin_page():
    """Render the LinkedIn page."""
    return render_template("linkedin.html")

@app.route("/signup")
def signup_page():
    """Render the signup/registration page."""
    return render_template("signup.html")


@app.route('/api/login', methods=['GET', 'POST'])
def login():
    """Authenticate user and return JWT token."""
    if request.method == 'GET':
        return jsonify({
            'message': 'Use POST to /api/login with JSON: {username, password}.'
        }), 200

    data = parse_json_request()
    if data is None:
        return jsonify({'message': 'Invalid or missing JSON payload'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Missing username or password'}), 400

    users = load_users()
    user = users.get(username)

    if not user or not check_password_hash(user['password'], password):
        return jsonify({'message': 'Invalid username or password'}), 401

   
    otp = str(secrets.randbelow(900000) + 100000)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
    pending_logins[username] = {
        'otp': otp,
        'expires_at': expires_at
    }

  
    sent = False
    try:
        user_email = users.get(username, {}).get('email')
        if user_email:
            sent = send_otp_via_email(user_email, otp)
    except Exception:
        sent = False

    if not sent:
    
        try:
            user_phone = users.get(username, {}).get('phone')
            if user_phone:
                sent = send_otp_via_twilio(user_phone, otp)
        except Exception:
            sent = False

    if sent:
        return jsonify({'message': 'OTP sent', 'otp_required': True}), 200

    return jsonify({'message': 'OTP required', 'otp_required': True, 'otp': otp}), 200


@app.route('/api/login/verify', methods=['POST'])
def login_verify():
    """Verify OTP for login and return JWT token."""
    data = parse_json_request()
    if data is None:
        return jsonify({'message': 'Invalid or missing JSON payload'}), 400

    username = data.get('username')
    otp = data.get('otp')
    if not username or not otp:
        return jsonify({'message': 'Missing username or otp'}), 400

    pending = pending_logins.get(username)
    if not pending:
        return jsonify({'message': 'No pending login found'}), 404

    if datetime.datetime.now(datetime.timezone.utc) > pending['expires_at']:
        pending_logins.pop(username, None)
        return jsonify({'message': 'OTP expired'}), 400

    if otp != pending['otp']:
        return jsonify({'message': 'Invalid OTP'}), 400

   
    token = jwt.encode({
        'username': username,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    pending_logins.pop(username, None)
    return jsonify({'token': token})

@app.route('/api/signup', methods=['GET', 'POST'])
def signup():
    """Register a new user account."""
    if request.method == 'GET':
        return jsonify({
            'message': 'Existing users stored in the database',
            'users': get_all_users()
        }), 200

    data = parse_json_request()
    if data is None:
        return jsonify({'message': 'Invalid or missing JSON payload'}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    dateofbirth = data.get('dateofbirth')
    registered_at = datetime.datetime.now(datetime.timezone.utc)
    
    return jsonify({'message': 'Use /api/signup/start to initiate signup with OTP'}), 400


@app.route('/api/signup/start', methods=['POST'])
def signup_start():
    """Begin signup: validate input, create pending entry and send OTP (demo returns OTP)."""
    data = parse_json_request()
    if data is None:
        return jsonify({'message': 'Invalid or missing JSON payload'}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    dateofbirth = data.get('dateofbirth')
    phone = data.get('phone')

    if not all([username, email, password, dateofbirth]):
        return jsonify({'message': 'Missing registration fields'}), 400

    users = load_users()
    if username in users:
        return jsonify({'message': 'User already exists'}), 400

    
    otp = str(secrets.randbelow(900000) + 100000)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
    pending_signups[username] = {
        'username': username,
        'email': email,
        'password': password,
        'dateofbirth': dateofbirth,
        'phone': phone,
        'otp': otp,
        'expires_at': expires_at
    }

   
    sent = False
    if email:
        sent = send_otp_via_email(email, otp)

    if not sent and phone:
        pending_signups[username]['phone'] = phone
        sent = send_otp_via_twilio(phone, otp)

    if sent:
        return jsonify({'message': 'OTP sent'}), 200
    
    return jsonify({'message': 'OTP sent (demo)', 'otp': otp}), 200


@app.route('/api/signup/verify', methods=['POST'])
def signup_verify():
    """Verify OTP and create the user account."""
    data = parse_json_request()
    if data is None:
        return jsonify({'message': 'Invalid or missing JSON payload'}), 400

    username = data.get('username')
    otp = data.get('otp')
    if not username or not otp:
        return jsonify({'message': 'Missing username or otp'}), 400

    pending = pending_signups.get(username)
    if not pending:
        return jsonify({'message': 'No pending signup found'}), 404

    if datetime.datetime.now(datetime.timezone.utc) > pending['expires_at']:
        pending_signups.pop(username, None)
        return jsonify({'message': 'OTP expired'}), 400

    if otp != pending['otp']:
        return jsonify({'message': 'Invalid OTP'}), 400

    # create user
    users = load_users()
    if username in users:
        pending_signups.pop(username, None)
        return jsonify({'message': 'User already exists'}), 400

    hashed_password = generate_password_hash(pending['password'])
    save_user(
        username,
        hashed_password,
        pending['email'],
        pending['dateofbirth'],
        pending.get('phone'),
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
    pending_signups.pop(username, None)
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Retrieve authenticated user's profile information. Requires valid JWT token."""
    token = get_bearer_token()
    if not token:
        return jsonify({'message': 'Token is missing or malformed'}), 401

    try:
        decoded_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        username = decoded_data.get('username')
        if not username:
            return jsonify({'message': 'Token payload is invalid'}), 401
        users = load_users()
        user_info = users.get(username)

        if not user_info:
            return jsonify({'message': 'User no longer exists'}), 404

        return jsonify({
            "message": f"Welcome {username} to your profile panel!",
            "username": username,
            "email": user_info.get("email"),
            "phone": user_info.get("phone"),
            "dateofbirth": user_info.get("dateofbirth"),
            "registered_at": user_info.get("registered_at")
        }), 200

    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Token is invalid'}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
