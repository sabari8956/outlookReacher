# OutlookReacher

OutlookReacher is a Flask-based web application that enables automated email campaigns through Microsoft Outlook integration. It provides a user-friendly interface for processing CSV data, managing email templates, and visualizing campaign statistics.

## Features

### 1. Microsoft Authentication
- Secure Microsoft OAuth2 authentication
- Seamless integration with Outlook/Microsoft 365
- Token-based session management

### 2. CSV Processing
- Smart CSV file upload with automatic delimiter detection
- Support for multiple encodings (UTF-8, Latin-1, CP1252, ISO-8859-1)
- Automatic email validation and column detection
- CSV data preview functionality
- Handles various CSV formats (comma, pipe, semicolon, tab-delimited)

### 3. Email Campaign Management
- Dynamic email template system with variable placeholders
- Real-time template preview with sample data
- Bulk email sending with error handling
- HTML email content support
- Smart variable replacement from CSV columns
- Campaign progress tracking and statistics
- Support for personalized subject lines

### 4. Data Visualization
- Interactive charts using Plotly
- Campaign statistics visualization
- Distribution analysis of numeric data
- Real-time data preview
- Automated chart generation for numeric columns

### 5. User Interface
- Clean, responsive Bootstrap-based design
- Tabbed interface for different features
- Flash messages for user feedback
- Mobile-friendly layout
- Interactive template editor with variable helper
- Real-time template preview

## Development Setup

### Prerequisites
- Python 3.12 or higher
- uv package manager
- Microsoft Azure account with registered application

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd OutlookReacher
```

2. Create and activate a Python virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate     # Windows
```

3. Install dependencies using uv:
```bash
uv venv
uv pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your Azure credentials:
```
FLASK_SECRET_KEY=your_secret_key
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_TENANT_ID=your_azure_tenant_id
```

## Azure Configuration

1. Register a new application in Azure Active Directory:
   - Go to Azure Portal > Azure Active Directory > App registrations
   - Click "New registration"
   - Enter application name and configure platform as Web

2. Configure required permissions:
   - Microsoft Graph API permissions:
     - Mail.Send
     - User.Read

3. Set up authentication:
   - Add redirect URI: `http://localhost:5000/auth-callback`
   - Create a client secret and save it securely
   - Note down Client ID and Tenant ID

## Usage

1. Start the application:
```bash
python main.py
```

2. Access the application:
   - Open browser and navigate to `http://localhost:5000`
   - Sign in with your Microsoft account
   - Upload a CSV file containing email addresses
   - Create an email template using available variables
   - Preview and send your email campaign

## CSV File Requirements

- Must contain at least one column with valid email addresses
- Supported delimiters: comma (,), pipe (|), semicolon (;), tab
- File size limit: 16MB
- Supported encodings: UTF-8, Latin-1, CP1252, ISO-8859-1
- BOM (Byte Order Mark) is automatically handled

## Email Template Variables

Use double curly braces to insert variables from your CSV:
- Example: `Hello {{Name}},`
- All CSV columns are available as variables
- Real-time preview shows actual values
- Supports both subject line and body variables
- HTML content is supported

## Security Features

- CSRF protection enabled
- Secure session management
- Microsoft OAuth2 authentication
- File upload validation and sanitization
- Rate limiting for API calls
- Secure token handling

## Project Structure

```
OutlookReacher/
├── main.py              # Main application file
├── templates/           # HTML templates
│   ├── base.html       # Base template with common styles
│   ├── dashboard.html  # Main dashboard interface
│   ├── login.html     # Authentication page
│   └── partials/      # Reusable components
├── uploads/            # CSV file storage (gitignored)
├── flask_session/      # Session storage (gitignored)
└── static/            # Static assets
```

## Error Handling

- Automatic delimiter detection with fallback
- Multiple encoding attempt strategy
- Invalid email detection and reporting
- Campaign sending error tracking
- User-friendly error messages
- Session state recovery

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Create a Pull Request

## Author

Sabari K

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Flask web framework
- Microsoft Graph API
- Pandas for data processing
- Plotly for visualizations
- Bootstrap for UI components
- MSAL for Microsoft authentication