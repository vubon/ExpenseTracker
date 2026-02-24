"""
Installation manager for guided OAuth setup.
Helps users create their own Google Cloud OAuth app for better privacy and security.
"""

import os
import sys
import json
import webbrowser
from tracker.etd import ETDHandler
from tracker.logs_config import logger


class InstallationManager:
    """Manages the guided installation flow for user-owned OAuth apps."""
    
    OAUTH_CREDENTIALS_FILE = 'oauth_credentials.json'
    
    # URLs for Google Cloud Console
    URLS = {
        'create_project': 'https://console.cloud.google.com/projectcreate',
        'enable_gmail_api': 'https://console.cloud.google.com/apis/library/gmail.googleapis.com',
        'create_credentials': 'https://console.cloud.google.com/apis/credentials',
    }
    
    def __init__(self):
        self.etd_handler = ETDHandler()
        self.credentials_path = self.etd_handler.get_path(self.OAUTH_CREDENTIALS_FILE)
    
    def run(self):
        """Execute the guided installation flow."""
        self._print_welcome()
        
        if not self._confirm_start():
            print("\nInstallation cancelled.")
            return False
        
        # Step 1: Create Google Cloud Project
        self._step_create_project()
        
        # Step 2: Enable Gmail API
        self._step_enable_gmail_api()
        
        # Step 3: Create OAuth Credentials
        client_id, client_secret = self._step_create_credentials()
        
        # Step 4: Save credentials
        if not self._save_credentials(client_id, client_secret):
            return False
        
        # Step 5: Authenticate
        if not self._step_authenticate():
            return False
        
        self._print_success()
        return True
    
    def _print_welcome(self):
        """Print welcome message."""
        print("\n" + "━" * 60)
        print(" Welcome to Expense Tracker Setup")
        print("━" * 60)
        print()
        print("For security and privacy, you'll create your own Google Cloud OAuth app.")
        print("This ensures YOUR data stays under YOUR control.")
        print()
        print("Estimated time: 7 minutes (one-time setup)")
        print()
    
    def _confirm_start(self) -> bool:
        """Ask user confirmation to start."""
        response = input("Ready to begin? [Y/n]: ").strip().lower()
        return response in ('', 'y', 'yes')
    
    def _step_create_project(self):
        """Guide user through creating Google Cloud project."""
        print("\n" + "━" * 60)
        print(" Step 1/3: Create Google Cloud Project")
        print("━" * 60)
        print()
        print("Opening Google Cloud Console in your browser...")
        print()
        
        try:
            webbrowser.open(self.URLS['create_project'])
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")
            print(f"⚠️  Could not open browser automatically.")
            print(f"Please manually visit: {self.URLS['create_project']}")
        
        print("Please follow these steps:")
        print("1. Click 'Create Project'")
        print("2. Name it anything (e.g., 'My Expense Tracker')")
        print("3. Click 'Create'")
        print("4. Come back here when done")
        print()
        input("Press ENTER when you've created the project...")
    
    def _step_enable_gmail_api(self):
        """Guide user through enabling Gmail API."""
        print("\n" + "━" * 60)
        print(" Step 2/3: Enable Gmail API")
        print("━" * 60)
        print()
        print("Opening Gmail API page in your browser...")
        print()
        
        try:
            webbrowser.open(self.URLS['enable_gmail_api'])
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")
            print(f"⚠️  Could not open browser automatically.")
            print(f"Please manually visit: {self.URLS['enable_gmail_api']}")
        
        print("Please follow these steps:")
        print("1. Click the blue 'Enable' button")
        print("2. Wait for it to activate (5-10 seconds)")
        print("3. Come back here when done")
        print()
        input("Press ENTER when Gmail API is enabled...")
    
    def _step_create_credentials(self) -> tuple:
        """Guide user through creating OAuth credentials."""
        print("\n" + "━" * 60)
        print(" Step 3/3: Create OAuth Credentials")
        print("━" * 60)
        print()
        print("Opening Credentials page in your browser...")
        print()
        
        try:
            webbrowser.open(self.URLS['create_credentials'])
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")
            print(f"⚠️  Could not open browser automatically.")
            print(f"Please manually visit: {self.URLS['create_credentials']}")
        
        print("Please follow these steps:")
        print("1. Click 'Create Credentials' → 'OAuth client ID'")
        print("2. Choose 'Desktop app' as application type")
        print("3. Name it 'etracker' (or anything you like)")
        print("4. Click 'Create'")
        print("5. You'll see CLIENT_ID and CLIENT_SECRET")
        print()
        print("Now, copy and paste them here:")
        print()
        
        # Get CLIENT_ID
        while True:
            client_id = input("CLIENT_ID: ").strip()
            if client_id:
                break
            print("⚠️  CLIENT_ID cannot be empty. Please try again.")
        
        # Get CLIENT_SECRET
        while True:
            client_secret = input("CLIENT_SECRET: ").strip()
            if client_secret:
                break
            print("⚠️  CLIENT_SECRET cannot be empty. Please try again.")
        
        print()
        print("✓ Credentials received!")
        
        return client_id, client_secret
    
    def _save_credentials(self, client_id: str, client_secret: str) -> bool:
        """Save OAuth credentials to file."""
        credentials_data = {
            'installed': {
                'client_id': client_id,
                'client_secret': client_secret,
                'project_id': 'user-expense-tracker',
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
                'redirect_uris': ['http://localhost']
            }
        }
        
        try:
            # Ensure .etd directory exists
            os.makedirs(os.path.dirname(self.credentials_path), exist_ok=True, mode=0o700)
            
            # Write credentials file
            with open(self.credentials_path, 'w') as f:
                json.dump(credentials_data, f, indent=2)
            
            # Set secure permissions (read/write for owner only)
            os.chmod(self.credentials_path, 0o600)
            
            print("✓ Credentials saved securely!")
            logger.info(f"OAuth credentials saved to {self.credentials_path}")
            return True
            
        except Exception as e:
            print(f"\n✗ Error saving credentials: {e}")
            logger.error(f"Failed to save credentials: {e}")
            return False
    
    def _step_authenticate(self) -> bool:
        """Guide user through authentication."""
        print("\n" + "━" * 60)
        print(" Final Step: Authenticate")
        print("━" * 60)
        print()
        print("Opening browser for Google authentication...")
        print("(Browser opens with Google OAuth consent screen)")
        print()
        print("User clicks: 'Allow' ← Give etracker permission to read Gmail")
        print()
        
        try:
            # Import here to avoid circular dependency
            from tracker.gmail_authenticator import GmailAuthenticator
            
            authenticator = GmailAuthenticator()
            authenticator.authenticate()
            
            print("\n✓ Authentication successful!")
            print(f"✓ Token saved securely at: {authenticator.token_file}")
            return True
            
        except Exception as e:
            print(f"\n✗ Authentication failed: {e}")
            logger.error(f"Authentication failed during installation: {e}")
            return False
    
    def _print_success(self):
        """Print success message."""
        print()
        print("✓ Google Cloud project: Ready")
        print("✓ Gmail API: Enabled")
        print("✓ OAuth app: Created and configured")
        print()
        print("━" * 60)
        print(" Setup Complete! 🎉")
        print("━" * 60)
        print()
        print("You can now start tracking expenses!")
        print()
        print("Try: etracker --continuous")
        print()
    
    def is_installed(self) -> bool:
        """Check if installation is complete."""
        from tracker.gmail_authenticator import GmailAuthenticator
        authenticator = GmailAuthenticator()
        
        # Check if both credentials and token exist
        has_credentials = os.path.exists(self.credentials_path)
        has_token = os.path.exists(authenticator.token_file)
        
        return has_credentials and has_token
