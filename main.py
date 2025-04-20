from flask import Flask, redirect, request, session, url_for, render_template_string
import msal
import os
from dotenv import load_dotenv
import requests
from flask_session import Session
# Load environment variables
load_dotenv()

app = Flask(__name__)

if not os.getenv('FLASK_SECRET_KEY'):
    raise ValueError("No FLASK_SECRET_KEY set in environment variables")

app.config["SESSION_TYPE"] = "filesystem"  
app.config["SECRET_KEY"] = os.getenv('FLASK_SECRET_KEY')
Session(app)


# Azure AD configuration
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
TENANT_ID = os.getenv('AZURE_TENANT_ID')
AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
SCOPE = ['https://graph.microsoft.com/Mail.Send', 'https://graph.microsoft.com/User.Read']
REDIRECT_PATH = "/auth-callback"

# HTML templates
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OutlookReacher</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .btn { padding: 10px 20px; background: #0078d4; color: white; text-decoration: none; border-radius: 4px; }
        .form-group { margin-bottom: 15px; }
        input, textarea { width: 100%; padding: 8px; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        {% if user %}
            <h1>Welcome, {{ user.get('displayName', 'User') }}!</h1>
            <div class="form-group">
                <h2>Send Email</h2>
                <form method="POST" action="{{ url_for('send_email') }}">
                    <div class="form-group">
                        <label>To:</label>
                        <input type="email" name="to" required>
                    </div>
                    <div class="form-group">
                        <label>Subject:</label>
                        <input type="text" name="subject" required>
                    </div>
                    <div class="form-group">
                        <label>Message (HTML supported):</label>
                        <textarea name="body" rows="10" required></textarea>
                    </div>
                    <button type="submit" class="btn">Send Email</button>
                </form>
            </div>
            <p><a href="{{ url_for('logout') }}">Logout</a></p>
        {% else %}
            <h1>Welcome to OutlookReacher</h1>
            <p><a href="{{ url_for('login') }}" class="btn">Sign in with Microsoft</a></p>
        {% endif %}
    </div>
</body>
</html>
"""

def get_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

def get_user_info(token):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(
        'https://graph.microsoft.com/v1.0/me',
        headers=headers
    )
    return response.json() if response.ok else None

@app.route('/')
def index():
    if not session.get('user'):
        return render_template_string(INDEX_TEMPLATE, user=None)
    
    token = session.get('token_cache', {}).get('access_token')
    user = get_user_info(token)
    return render_template_string(INDEX_TEMPLATE, user=user)

@app.route('/login')
def login():
    auth_url = get_msal_app().get_authorization_request_url(
        SCOPE,
        redirect_uri=url_for('auth_callback', _external=True)
    )
    return redirect(auth_url)

@app.route('/auth-callback')
def auth_callback():
    token = get_msal_app().acquire_token_by_authorization_code(
        request.args['code'],
        scopes=SCOPE,
        redirect_uri=url_for('auth_callback', _external=True)
    )
    
    if 'error' in token:
        return f"Error: {token['error']}"
    
    session['token_cache'] = token
    session['user'] = True
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/send-email', methods=['POST'])
def send_email():
    if not session.get('user'):
        return redirect(url_for('login'))

    token = session.get('token_cache', {}).get('access_token')
    if not token:
        return redirect(url_for('login'))

    to_email = request.form.get('to')
    subject = request.form.get('subject')
    body = request.form.get('body')

    # Prepare the email message
    email_msg = {
        'message': {
            'subject': subject,
            'body': {
                'contentType': 'HTML',
                'content': body
            },
            'toRecipients': [{'emailAddress': {'address': to_email}}]
        }
    }

    # Send the email using Microsoft Graph API
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        'https://graph.microsoft.com/v1.0/me/sendMail',
        headers=headers,
        json=email_msg
    )

    if response.ok:
        return 'Email sent successfully!'
    else:
        return f'Error sending email: {response.text}'

if __name__ == '__main__':
    app.run(debug=True, port=5000)
