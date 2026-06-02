from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import jwt
import datetime
from pymongo import MongoClient
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


MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set")

client = MongoClient(MONGO_URI)
db = client["user_auth_db"]
users_collection = db["users"]

users_collection.create_index("username", unique=True)
users_collection.create_index("email", unique=True)


pending_logins_col = db["pending_logins"]
pending_signups_col = db["pending_signups"]


pending_logins_col.create_index("expires_at", expireAfterSeconds=0)
pending_signups_col.create_index("expires_at", expireAfterSeconds=0)


pending_logins_col.create_index("username", unique=True)
pending_signups_col.create_index("username", unique=True)


def get_user(username):
    return users_collection.find_one({"username": username})

def get_user_by_email(email):
    return users_collection.find_one({"email": email})

def create_user(username, password, email, dateofbirth, phone, registered_at):
    users_collection.insert_one({
        "username": username,
        "password": password,
        "email": email,
        "dateofbirth": dateofbirth,
        "phone": phone,
        "registered_at": registered_at
    })

def get_all_users():
    return list(
        users_collection.find(
            {},
            {
                "_id": 0,
                "password": 0
            }
        )
    )

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
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/profile")
def profile_page():
    return render_template("profile.html")

@app.route("/education")
def education_page():
    return render_template("education.html")

@app.route("/games")
def games_page():
    return render_template("games.html")

@app.route("/github")
def github_page():
    return render_template("github.html")

@app.route("/linkedin")
def linkedin_page():
    return render_template("linkedin.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route('/api/login', methods=['GET', 'POST'])
def login():
    """Authenticate user, send OTP, store pending login in MongoDB."""
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

    user = get_user(username)

    if not user or not check_password_hash(user['password'], password):
        return jsonify({'message': 'Invalid username or password'}), 401

   
    otp = str(secrets.randbelow(900000) + 100000)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)

    
    pending_logins_col.update_one(
        {"username": username},
        {"$set": {
            "otp": otp,
            "expires_at": expires_at,
            "email": user.get('email'),
            "phone": user.get('phone')
        }},
        upsert=True
    )

  
    sent = False
    user_email = user.get('email')
    if user_email:
        sent = send_otp_via_email(user_email, otp)

    if not sent:
        user_phone = user.get('phone')
        if user_phone:
            sent = send_otp_via_twilio(user_phone, otp)

    if sent:
        return jsonify({'message': 'OTP sent', 'otp_required': True}), 200

  
    return jsonify({'message': 'OTP required', 'otp_required': True, 'otp': otp}), 200


@app.route('/api/login/verify', methods=['POST'])
def login_verify():
    """Verify OTP from MongoDB, issue JWT if correct."""
    data = parse_json_request()
    if data is None:
        return jsonify({'message': 'Invalid or missing JSON payload'}), 400

    username = data.get('username')
    otp = data.get('otp')
    if not username or not otp:
        return jsonify({'message': 'Missing username or otp'}), 400

    
    pending = pending_logins_col.find_one({"username": username})
    if not pending:
        return jsonify({'message': 'No pending login found'}), 404

    if datetime.datetime.now(datetime.timezone.utc) > pending['expires_at']:
        pending_logins_col.delete_one({"username": username})
        return jsonify({'message': 'OTP expired'}), 400

    if otp != pending['otp']:
        return jsonify({'message': 'Invalid OTP'}), 400

    pending_logins_col.delete_one({"username": username})

    token = jwt.encode({
        'username': username,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'token': token}), 200


@app.route('/api/signup', methods=['GET', 'POST'])
def signup():
    """List users or inform to use /signup/start."""
    if request.method == 'GET':
        return jsonify({
            'message': 'Existing users stored in the database',
            'users': get_all_users()
        }), 200

    return jsonify({'message': 'Use /api/signup/start to initiate signup with OTP'}), 400


@app.route('/api/signup/start', methods=['POST'])
def signup_start():
    """Validate input, store pending signup in MongoDB, send OTP."""
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

   
    if get_user(username) or get_user_by_email(email):
        return jsonify({'message': 'User already exists'}), 400

    
    otp = str(secrets.randbelow(900000) + 100000)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)

   
    pending_signups_col.update_one(
        {"username": username},
        {"$set": {
            "username": username,
            "email": email,
            "password": password,         
            "dateofbirth": dateofbirth,
            "phone": phone,
            "otp": otp,
            "expires_at": expires_at
        }},
        upsert=True
    )

   
    sent = False
    if email:
        sent = send_otp_via_email(email, otp)
    if not sent and phone:
        sent = send_otp_via_twilio(phone, otp)

    if sent:
        return jsonify({'message': 'OTP sent'}), 200

    return jsonify({'message': 'OTP sent (demo)', 'otp': otp}), 200


@app.route('/api/signup/verify', methods=['POST'])
def signup_verify():
    """Verify OTP, create user in MongoDB, delete pending record."""
    data = parse_json_request()
    if data is None:
        return jsonify({'message': 'Invalid or missing JSON payload'}), 400

    username = data.get('username')
    otp = data.get('otp')
    if not username or not otp:
        return jsonify({'message': 'Missing username or otp'}), 400

    pending = pending_signups_col.find_one({"username": username})
    if not pending:
        return jsonify({'message': 'No pending signup found'}), 404

   
    if datetime.datetime.now(datetime.timezone.utc) > pending['expires_at']:
        pending_signups_col.delete_one({"username": username})
        return jsonify({'message': 'OTP expired'}), 400

   
    if otp != pending['otp']:
        return jsonify({'message': 'Invalid OTP'}), 400

    
    if get_user(username) or get_user_by_email(pending['email']):
        pending_signups_col.delete_one({"username": username})
        return jsonify({'message': 'User already exists'}), 400

    
    hashed_password = generate_password_hash(pending['password'])
    create_user(
        username,
        hashed_password,
        pending['email'],
        pending['dateofbirth'],
        pending.get('phone'),
        datetime.datetime.now(datetime.timezone.utc)
    )

   
    pending_signups_col.delete_one({"username": username})

    return jsonify({'message': 'User created successfully'}), 201


@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Return profile info for authenticated user (JWT required)."""
    token = get_bearer_token()
    if not token:
        return jsonify({'message': 'Token is missing or malformed'}), 401

    try:
        decoded_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        username = decoded_data.get('username')
        if not username:
            return jsonify({'message': 'Token payload is invalid'}), 401

        user = get_user(username)
        if not user:
            return jsonify({'message': 'User no longer exists'}), 404

        return jsonify({
            "message": f"Welcome {username} to your profile panel!",
            "username": username,
            "email": user.get("email"),
            "phone": user.get("phone"),
            "dateofbirth": user.get("dateofbirth"),
            "registered_at": user.get("registered_at")
        }), 200

    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Token is invalid'}), 401



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)