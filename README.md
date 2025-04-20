# OutlookReacher

A Python-based Microsoft Mail Authentication & Sending Bot that allows sending emails through Microsoft Graph API.

## Prerequisites

- Python 3.8 or higher
- A Microsoft Azure account
- Basic knowledge of Flask and web applications

## Step 1: Initial Setup

1. Clone this repository:
   ```bash
   git clone [your-repo-url]
   cd OutlookReacher
   ```

2. Install dependencies using uv:
   ```bash
   uv venv
   uv pip install flask msal requests python-dotenv
   ```

## Step 2: Microsoft Azure Setup

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to Azure Active Directory > App registrations > New registration
3. Register a new application:
   - Name: OutlookReacher (or your preferred name)
   - Supported account types: Select "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: http://localhost:5000/auth-callback

4. After registration, note down:
   - Application (client) ID
   - Directory (tenant) ID

5. Create a client secret:
   - Go to Certificates & secrets > New client secret
   - Note down the generated secret value

6. Configure API permissions:
   - Go to API permissions
   - Add Microsoft Graph permissions:
     - Mail.Send
     - User.Read
   - Click "Grant admin consent"

## Step 3: Environment Configuration

1. Create a `.env` file in the project root:
   ```env
   AZURE_CLIENT_ID=your_client_id
   AZURE_CLIENT_SECRET=your_client_secret
   AZURE_TENANT_ID=your_tenant_id
   FLASK_SECRET_KEY=your_random_secret_key
   ```

## Step 4: Running the Application

1. Start the Flask application:
   ```bash
   python main.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Step 5: Authentication Flow

1. Click "Sign in with Microsoft"
2. You'll be redirected to Microsoft's login page
3. Enter your Microsoft account credentials
4. Grant the requested permissions
5. You'll be redirected back to the dashboard

## Step 6: Using the Email Sender

1. From the dashboard, navigate to "Compose Email"
2. Fill in the required fields:
   - Recipient(s) email address
   - Subject
   - HTML content for the email body
3. Click "Send Email"
4. Check the success/failure notification

## Features

- Microsoft OAuth2 authentication
- Secure token storage and refresh
- HTML email support
- Multiple recipient support
- Error handling and notifications
- Responsive UI

## Security Notes

- Never commit your `.env` file
- Store tokens securely
- Implement rate limiting for production use
- Use HTTPS in production

## Troubleshooting

1. Authentication Issues:
   - Verify Azure app registration settings
   - Check redirect URI configuration
   - Ensure all required permissions are granted

2. Email Sending Issues:
   - Verify token validity
   - Check recipient email format
   - Review HTML content formatting

## Contributing

Feel free to open issues or submit pull requests to improve this project.

## License

This project is licensed under the MIT License - see the LICENSE file for details.