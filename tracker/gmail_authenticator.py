import os
import pickle

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache

from tracker.etd import ETDHandler
from tracker.logs_config import logger

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


class MemoryCache(Cache):
    _CACHE = {}

    def get(self, url):
        return self._CACHE.get(url)

    def set(self, url, content):
        self._CACHE[url] = content


class GmailAuthenticator:
    """
        Handles Gmail API Authentication and Service creation.
        Supports both user-owned OAuth apps (oauth_credentials.json) and legacy credentials.json.
    """

    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.etd_handler = ETDHandler()
        
        # Check for user-owned OAuth credentials first (new way)
        self.oauth_credentials_file = self.etd_handler.get_path('oauth_credentials.json')
        
        # Fall back to legacy credentials.json (old way)
        self.credentials_file = self.etd_handler.get_path(credentials_file)
        
        self.token_file = self.etd_handler.get_path(token_file)
        self.service = None

    def _get_credentials_file(self) -> str:
        """Get the credentials file to use (prefer user-owned OAuth)."""
        if os.path.exists(self.oauth_credentials_file):
            return self.oauth_credentials_file
        return self.credentials_file

    def validate_auth_files(self) -> None:
        """Validate that credentials file exists."""
        creds_file = self._get_credentials_file()
        
        if not os.path.exists(creds_file):
            raise FileNotFoundError(
                f"Missing Google OAuth credentials file.\n\n"
                f"To set up authentication, run:\n"
                f"  etracker install\n\n"
                f"This will guide you through creating your own OAuth app.\n"
                f"(Legacy: You can also manually place credentials.json in ~/.etd/)"
            )

    def authenticate(self):
        """
        Authenticate and return the Gmail API service with token persistence.
        """
        creds = None
        # Check if token.pickle exists to load credentials
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials or the token is expired, request new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())  # Refresh the token
            else:
                self.validate_auth_files()
                # Start the OAuth flow to get credentials
                creds_file = self._get_credentials_file()
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for future use
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

            try:
                os.chmod(self.token_file, 0o600)
            except OSError as err:
                logger.warning(f"Unable to set secure permissions on token file: {err}")

        # Build and return the Gmail API service
        self.service = build('gmail', 'v1', credentials=creds, cache=MemoryCache())
        return self.service
