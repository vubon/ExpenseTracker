import os
import pickle

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache

from tracker.etd import ETDHandler
from tracker.logs_config import logger # Added logger import

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
"""list: Defines the Gmail API scopes required by the application.
Currently set to `gmail.modify` to allow reading and modifying emails (e.g., marking as read).
"""


class MemoryCache(Cache):
    """A simple in-memory cache for the Google API client.

    This class implements the `googleapiclient.discovery_cache.base.Cache`
    interface, storing API discovery documents in a class-level dictionary.
    """
    _CACHE = {}

    def get(self, url: str) -> str | None:
        """Retrieves an item from the cache.

        Args:
            url (str): The URL (key) of the item to retrieve.

        Returns:
            str | None: The cached content if found, otherwise None.
        """
        return self._CACHE.get(url)

    def set(self, url: str, content: str) -> None:
        """Adds an item to the cache.

        Args:
            url (str): The URL (key) of the item to cache.
            content (str): The content to cache.
        """
        self._CACHE[url] = content


class GmailAuthenticator:
    """Handles Gmail API authentication and service creation.

    This class manages the OAuth 2.0 flow for authenticating with the Gmail API.
    It stores and refreshes access tokens, and provides an authenticated
    Gmail API service object.
    """

    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.pickle'):
        """Initializes the GmailAuthenticator.

        Args:
            credentials_file (str, optional): The name of the JSON file containing
                OAuth 2.0 client credentials. Defaults to 'credentials.json'.
                This file is expected to be in the path managed by `ETDHandler`.
            token_file (str, optional): The name of the file to store the OAuth 2.0
                access token. Defaults to 'token.pickle'. This file is also
                expected to be in the path managed by `ETDHandler`.

        Attributes:
            etd_handler (ETDHandler): Handler for resolving file paths.
            credentials_file (str): Absolute path to the credentials file.
            token_file (str): Absolute path to the token file.
            service: Authenticated Gmail API service instance, None until `authenticate` is called.
        """
        self.etd_handler = ETDHandler()
        self.credentials_file = self.etd_handler.get_path(credentials_file)
        self.token_file = self.etd_handler.get_path(token_file)
        self.service = None

    def authenticate(self) -> Any:
        """Authenticates with the Gmail API and returns an API service object.

        Handles loading, validating, and refreshing OAuth 2.0 credentials.
        If valid credentials are not available or are expired, it initiates
        the OAuth 2.0 authorization flow, which may require user interaction
        via a web browser.
        The obtained credentials (access token) are saved to `self.token_file`
        for future use.

        Returns:
            Any: An authenticated Gmail API service object (typically a
                `googleapiclient.discovery.Resource` instance) ready for use.

        Raises:
            Exception: Can raise exceptions related to file I/O (e.g., if
                `credentials.json` is not found or `token.pickle` cannot be written),
                or errors from the Google Auth library during the OAuth flow
                (e.g., `google.auth.exceptions.RefreshError` if the refresh token
                is invalid).
        """
        creds = None
        try:
            # Check if token.pickle exists to load credentials
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
        except (pickle.UnpicklingError, EOFError, AttributeError, ImportError, IndexError) as e:
            logger.warning(f"Error loading token from {self.token_file}: {e}. Will attempt to re-authenticate.")
            creds = None # Ensure creds is None if token is corrupted

        # If no valid credentials or the token is expired, request new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())  # Refresh the token
                except Exception as e: # Catch broad exceptions during refresh
                    logger.warning(f"Error refreshing token: {e}. Will attempt full re-authentication.")
                    creds = None # Force re-authentication

            if not creds or not creds.valid: # Re-check creds after potential refresh failure
                try:
                    # Start the OAuth flow to get credentials
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except FileNotFoundError:
                    logger.error(f"Credentials file not found at {self.credentials_file}. "
                                 "Please ensure 'credentials.json' is in the correct location (~/.etd/).")
                    raise # Re-raise to stop execution if credentials file is critical
                except Exception as e: # Catch other errors during OAuth flow
                    logger.error(f"Error during OAuth flow: {e}")
                    raise # Re-raise for other critical OAuth errors

            # Save the credentials for future use
            try:
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info(f"Credentials saved to {self.token_file}")
            except Exception as e:
                logger.error(f"Error saving token to {self.token_file}: {e}")
                # Depending on policy, might want to raise here or just warn

        # Build and return the Gmail API service
        self.service = build('gmail', 'v1', credentials=creds, cache=MemoryCache())
        return self.service
