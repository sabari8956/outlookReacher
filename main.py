from flask import Flask, redirect, request, session, url_for, render_template, flash
import msal
import os
from dotenv import load_dotenv
import requests
from flask_session import Session
from werkzeug.utils import secure_filename
import pandas as pd
import plotly.express as px
import plotly.utils
import json
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired

# Load environment variables
load_dotenv()

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)

if not os.getenv('FLASK_SECRET_KEY'):
    raise ValueError("No FLASK_SECRET_KEY set in environment variables")

app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = os.getenv('FLASK_SECRET_KEY')
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
app.config["WTF_CSRF_ENABLED"] = True

Session(app)

# Azure AD configuration
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
TENANT_ID = os.getenv('AZURE_TENANT_ID')
AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
SCOPE = ['https://graph.microsoft.com/Mail.Send', 'https://graph.microsoft.com/User.Read']
REDIRECT_PATH = "/auth-callback"

class UploadForm(FlaskForm):
    csv_file = FileField('CSV File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    delimiter = SelectField('Delimiter', choices=[
        ('auto', 'Auto Detect'),
        (',', 'Comma (,)'),
        ('|', 'Pipe (|)'),
        (';', 'Semicolon (;)'),
        ('\t', 'Tab'),
    ], default='auto')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def detect_delimiter(filepath):
    """Detect the delimiter of a CSV file by reading the first few lines"""
    common_delimiters = [',', '|', ';', '\t']
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            # Read first few lines
            header = file.readline().strip()
            
            # Count occurrences of each delimiter
            counts = {delimiter: header.count(delimiter) for delimiter in common_delimiters}
            
            # Get the delimiter with maximum occurrence
            max_count = max(counts.values())
            if max_count > 0:
                return max(counts.items(), key=lambda x: x[1])[0]
    except Exception as e:
        print(f"Error detecting delimiter: {e}")
    
    # Default to comma if detection fails
    return ','

def process_csv(filepath, selected_delimiter='auto'):
    """Process CSV with multiple encoding attempts, cleanup and delimiter handling"""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    df = None
    errors = []
    
    # Detect delimiter if set to auto
    if selected_delimiter == 'auto':
        delimiter = detect_delimiter(filepath)
    else:
        delimiter = selected_delimiter

    for encoding in encodings:
        try:
            df = pd.read_csv(filepath, encoding=encoding, delimiter=delimiter)
            # Clean column names
            df.columns = df.columns.str.strip().str.replace('\ufeff', '')
            
            # Remove BOM if present
            if '\ufeff' in df.columns[0]:
                df.columns.values[0] = df.columns.values[0].replace('\ufeff', '')
            
            # Handle null values
            df = df.fillna('')

            # Email validation for all columns
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            stats = {
                'total_rows': len(df),
                'delimiter_used': delimiter,
                'email_columns': {},
                'valid_emails': {},
                'invalid_emails': {},
                'email_column_suggestions': [],
                'sample_data': df.iloc[0].to_dict() if len(df) > 0 else {},  # Add first row as sample
                'sample_values': {col: str(df[col].iloc[0]) if len(df) > 0 else '' for col in df.columns}  # Add sample values for each column
            }
            
            # Function to check if a value might be an email
            def is_email(value):
                if not isinstance(value, str):
                    return False
                value = str(value).strip().lower()
                return bool(re.match(email_pattern, value))
            
            # Check each column for email addresses
            for col in df.columns:
                # Convert column to string type for validation
                df[col] = df[col].astype(str)
                
                # Count valid emails in the column
                valid_mask = df[col].apply(is_email)
                valid_count = valid_mask.sum()
                total_count = len(df[col].replace('', pd.NA).dropna())
                
                if total_count > 0:
                    # Calculate percentage of valid emails in non-empty values
                    valid_percentage = (valid_count / total_count) * 100
                    
                    stats['email_columns'][col] = total_count
                    stats['valid_emails'][col] = valid_count
                    stats['invalid_emails'][col] = total_count - valid_count
                    
                    if valid_percentage >= 50 and valid_count > 0:
                        sample_emails = df[col][valid_mask].head(3).tolist()
                        
                        stats['email_column_suggestions'].append({
                            'name': col,
                            'valid_count': valid_count,
                            'total_count': total_count,
                            'percentage': valid_percentage,
                            'sample_emails': sample_emails
                        })
            
            stats['email_column_suggestions'].sort(key=lambda x: x['percentage'], reverse=True)
            
            # Create UTF-8 version with detected delimiter
            utf8_filepath = os.path.join(
                os.path.dirname(filepath),
                'utf8_' + os.path.basename(filepath)
            )
            df.to_csv(utf8_filepath, index=False, encoding='utf-8', sep=delimiter)
            return df, stats, None
            
        except Exception as e:
            errors.append(f"Failed with {encoding} encoding: {str(e)}")
            continue
    
    return None, None, f"Failed to process CSV with all encodings:\n" + "\n".join(errors)

def get_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

def get_user_info(token):
    if not token:
        return None
        
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers
        )
        if response.ok:
            return response.json()
    except Exception as e:
        print(f"Error getting user info: {e}")
    return None

@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    if not session.get('user'):
        return redirect(url_for('login'))
    
    form = UploadForm()
    if form.validate_on_submit():
        file = form.csv_file.data
        delimiter = form.delimiter.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Process CSV and store in session
            df, stats, error = process_csv(filepath, selected_delimiter=delimiter)
            if error:
                flash(f'Error processing CSV: {error}', 'error')
                return redirect(url_for('index'))
            
            session['csv_data'] = df.to_json()
            session['csv_columns'] = df.columns.tolist()
            session['csv_stats'] = stats
            
            # Create visualizations
            plots = []
            # Create basic visualizations for numeric columns
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            if len(numeric_cols) > 0:
                for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
                    fig = px.histogram(df, x=col, title=f'Distribution of {col}')
                    plots.append(fig.to_html(full_html=False))
            
            # Flash statistics message
            stats_msg = f"CSV Processed Successfully!\n"
            stats_msg += f"Total Records: {stats['total_rows']}\n"
            stats_msg += f"Delimiter Used: {stats['delimiter_used']}\n"
            for col, valid_count in stats['valid_emails'].items():
                invalid_count = stats['invalid_emails'][col]
                stats_msg += f"\nColumn '{col}':\n"
                stats_msg += f"- Valid Emails: {valid_count}\n"
                stats_msg += f"- Invalid Emails: {invalid_count}"
            
            flash(stats_msg, 'success')
            return render_template(
                'dashboard.html',
                user=get_user_info(session.get('token_cache', {}).get('access_token')),
                form=form,
                csv_data=df.head().to_html(classes='table table-striped table-hover'),
                csv_columns=df.columns.tolist(),
                plots=plots,
                csv_stats=stats
            )
    
    flash('Please select a valid CSV file', 'error')
    return redirect(url_for('index'))

@app.route('/setup-campaign', methods=['POST'])
def setup_campaign():
    if not session.get('user') or not session.get('csv_data'):
        return redirect(url_for('login'))
    
    email_column = request.form.get('email_column')
    subject = request.form.get('subject')
    template = request.form.get('template')
    
    if not all([email_column, subject, template]):
        flash('Please fill in all fields')
        return redirect(url_for('index'))
    
    df = pd.read_json(session['csv_data'])
    
    # Validate email column
    if email_column not in df.columns:
        flash('Invalid email column selected')
        return redirect(url_for('index'))
    
    # Validate email addresses
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    valid_mask = df[email_column].str.match(email_pattern, na=False)
    invalid_emails = df[~valid_mask][email_column].tolist()
    
    if len(invalid_emails) > 0:
        flash(f'Warning: Found {len(invalid_emails)} invalid email addresses in {email_column} column. These will be skipped: {", ".join(invalid_emails[:5])}{"..." if len(invalid_emails) > 5 else ""}', 'error')
    
    # Store campaign settings in session
    session['campaign'] = {
        'email_column': email_column,
        'subject': subject,
        'template': template
    }
    
    # Process and send emails
    success_count = 0
    error_count = 0
    token = session.get('token_cache', {}).get('access_token')
    
    # Filter out invalid emails
    df_valid = df[valid_mask]
    
    for _, row in df_valid.iterrows():
        try:
            # Replace template placeholders with row data
            body = template
            subject_text = subject
            for col in df.columns:
                placeholder = '{{' + col + '}}'
                if placeholder in template:
                    body = body.replace(placeholder, str(row[col]))
                if placeholder in subject:
                    subject_text = subject_text.replace(placeholder, str(row[col]))
            
            # Prepare email message
            email_msg = {
                'message': {
                    'subject': subject_text,
                    'body': {
                        'contentType': 'HTML',
                        'content': body
                    },
                    'toRecipients': [{'emailAddress': {'address': row[email_column]}}]
                }
            }
            
            # Send email
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
                success_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            error_count += 1
            continue
    
    flash(f'Campaign completed: {success_count} emails sent successfully, {error_count} failed, {len(invalid_emails)} invalid emails skipped')
    return redirect(url_for('index'))

@app.route('/')
def index():
    if not session.get('user'):
        return render_template('login.html')
    
    # Check if token exists and try to get user info
    token = session.get('token_cache', {}).get('access_token')
    user = get_user_info(token)
    
    # If token is invalid, clear session and redirect to login
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    form = UploadForm()
    
    # Get stored CSV data and visualizations if available
    csv_data = None
    csv_columns = session.get('csv_columns', [])
    csv_stats = session.get('csv_stats', None)
    plots = []
    
    if session.get('csv_data'):
        try:
            df = pd.read_json(session['csv_data'])
            csv_data = df.head().to_html(classes='table table-striped table-hover')
            
            # Recreate visualizations
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            if len(numeric_cols) > 0:
                for col in numeric_cols[:3]:
                    fig = px.histogram(df, x=col, title=f'Distribution of {col}')
                    plots.append(fig.to_html(full_html=False))
        except Exception as e:
            # If there's an error with the stored CSV data, clear it
            session.pop('csv_data', None)
            session.pop('csv_columns', None)
            session.pop('csv_stats', None)
            flash('There was an error loading the previous CSV data. Please upload again.', 'error')
    
    return render_template(
        'dashboard.html',
        user=user,
        form=form,
        csv_data=csv_data,
        csv_columns=csv_columns,
        plots=plots,
        csv_stats=csv_stats
    )

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
