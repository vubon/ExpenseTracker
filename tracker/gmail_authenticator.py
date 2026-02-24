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
    """

    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.etd_handler = ETDHandler()
        self.credentials_file = self.etd_handler.get_path(credentials_file)
        self.token_file = self.etd_handler.get_path(token_file)
        self.service = None

    def validate_auth_files(self) -> None:
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(
                f"Missing Google OAuth credentials file at: {self.credentials_file}. "
                "Download credentials.json from Google Cloud Console and place it in the .etd directory."
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
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
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
