# Flask Authentication Application

A clean, secure user authentication system built with Flask featuring JWT-based authentication and a modern, responsive UI.

## Features

 **User Registration** - Create new user accounts with email validation  
 **Secure Login** - Password hashing with Werkzeug security  
 **JWT Authentication** - Stateless session management with 30-minute token expiry  
 **Protected Routes** - Dashboard and profile only accessible to authenticated users  
 **Responsive Design** - Modern UI built with HTML5 and CSS  

 **CORS Support** - Enabled for cross-origin requests

## Project Structure

```
project2/
├── app.py                 # Flask application (backend)
├── requirements.txt       # Python dependencies
├── users.json            # User data storage (auto-created)
├── templates/            # HTML templates
│   ├── index.html        # Login page
│   ├── signup.html       # Registration page
│   ├── dashboard.html    # User dashboard
│   └── profile.html      # Profile page
└── static/               # Frontend assets
    ├── app.js            # JavaScript functionality
    └── style.css         # Styling
```

## Setup & Installation

### Prerequisites

- Python 3.8+
- Virtual Environment (recommended)

### Step 1: Create Virtual Environment

```bash
python -m venv 223344
```

### Step 2: Activate Virtual Environment

**Windows (PowerShell):**

```powershell
& .\223344\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```cmd
223344\Scripts\activate.bat
```

**Linux/Mac:**

```bash
source 223344/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run Application

```bash
python app.py
```

The application will start on `http://127.0.0.1:5000`

## Usage

### 1. **Register New Account**

- Go to http://127.0.0.1:5000/signup
- Fill in username, email, password, and date of birth
- Click "SIGN UP"
- You'll be redirected to login page

### 2. **Login**

- Enter your username and password
- Click "Login"
- On success, you'll be taken to the dashboard

### 3. **View Profile**

- From dashboard, click "View Profile"
- Your profile information will be displayed

### 4. **Logout**

- Click "Logout" button in dashboard
- Returns to login page

## API Endpoints

### POST `/api/login`

Authenticate user and receive JWT token.

**Request:**

```json
{
  "username": "john_doe",
  "password": "SecurePass123!"
}
```

**Response (200):**

```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### POST `/api/signup`

Register a new user account.

**Request:**

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "dateofbirth": "1995-05-15"
}
```

**Response (201):**

```json
{
  "message": "User created successfully"
}
```

### GET `/api/profile`

Retrieve authenticated user's profile information.

**Headers:**

```
Authorization: Bearer <JWT_TOKEN>
```

**Response (200):**

```json
{
  "message": "Welcome john_doe to your profile panel!",
  "username": "john_doe",
  "email": "john@example.com",
  "dateofbirth": "1995-05-15",
  "registered_at": "2026-06-01T05:12:09.607871+00:00"
}
```

## Error Handling

The API returns appropriate HTTP status codes:

| Status | Meaning                            |
| ------ | ---------------------------------- |
| 200    | Success                            |
| 201    | Resource created                   |
| 400    | Bad request / Missing fields       |
| 401    | Unauthorized / Invalid credentials |
| 404    | User not found                     |

## Security Features

 **Password Hashing** - Uses Werkzeug's secure hashing  
 **JWT Tokens** - Stateless authentication with expiration  
 **CORS** - Cross-Origin Resource Sharing enabled  
 **Input Validation** - Server-side validation of all inputs  
 **UTF-8 Encoding** - Safe file handling

## Configuration

### Environment Variables

```bash
# Set custom secret key for JWT
export SECRET_KEY="your-custom-secret-key-here"

# Set custom user data file location
export USER_DATA_FILE="/path/to/users.json"
```

## Data Storage

User data is stored in `users.json` with the following structure:

```json
{
  "john_doe": {
    "password": "$2b$12$...",
    "email": "john@example.com",
    "dateofbirth": "1995-05-15",
    "registered_at": "2026-06-01T05:12:09.607871+00:00"
  }
}
```

Passwords are hashed using bcrypt and are never stored in plain text.

## Dependencies

- **Flask** (3.1.3) - Web framework
- **Flask-CORS** (6.0.2) - CORS support
- **PyJWT** (2.13.0) - JWT token handling
- **Werkzeug** (3.1.8) - Security utilities

## Development Notes

- **Debug Mode**: Currently enabled for development. Disable in production.
- **Token Expiry**: Tokens expire after 30 minutes by default.
- **Database**: Currently uses JSON file. Consider PostgreSQL for production.

## License

This project is open source and available under the MIT License.

## Support

For issues or questions, please refer to the code comments or contact the development team.
