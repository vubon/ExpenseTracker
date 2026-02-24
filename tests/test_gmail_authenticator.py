import unittest
from unittest.mock import patch, MagicMock, mock_open

from tracker.gmail_authenticator import GmailAuthenticator


class TestGmailAuthenticator(unittest.TestCase):
    @patch('tracker.gmail_authenticator.ETDHandler')
    @patch('tracker.gmail_authenticator.os.path.exists')
    def test_validate_auth_files_missing_credentials(self, mock_exists, mock_etd_handler):
        mock_etd_handler.return_value.get_path.side_effect = lambda filename: f"/tmp/.etd/{filename}"
        mock_exists.side_effect = lambda path: False if path.endswith('credentials.json') else True

        authenticator = GmailAuthenticator()

        with self.assertRaises(FileNotFoundError) as context:
            authenticator.validate_auth_files()

        self.assertIn("Missing Google OAuth credentials file", str(context.exception))

    @patch('tracker.gmail_authenticator.ETDHandler')
    @patch('tracker.gmail_authenticator.os.chmod')
    @patch('tracker.gmail_authenticator.pickle.dump')
    @patch('tracker.gmail_authenticator.open', new_callable=mock_open)
    @patch('tracker.gmail_authenticator.InstalledAppFlow')
    @patch('tracker.gmail_authenticator.build')
    @patch('tracker.gmail_authenticator.os.path.exists')
    def test_authenticate_sets_token_file_permissions(
        self,
        mock_exists,
        mock_build,
        mock_installed_app_flow,
        mock_file,
        mock_pickle_dump,
        mock_chmod,
        mock_etd_handler
    ):
        mock_etd_handler.return_value.get_path.side_effect = lambda filename: f"/tmp/.etd/{filename}"
        mock_exists.side_effect = lambda path: path.endswith('credentials.json')

        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = False
        mock_creds.refresh_token = None

        mock_flow_instance = MagicMock()
        mock_flow_instance.run_local_server.return_value = mock_creds
        mock_installed_app_flow.from_client_secrets_file.return_value = mock_flow_instance

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        authenticator = GmailAuthenticator()
        service = authenticator.authenticate()

        self.assertEqual(service, mock_service)
        mock_pickle_dump.assert_called_once_with(mock_creds, mock_file())
        mock_chmod.assert_called_once_with('/tmp/.etd/token.pickle', 0o600)

    @patch('tracker.gmail_authenticator.ETDHandler')
    @patch('tracker.gmail_authenticator.logger.warning')
    @patch('tracker.gmail_authenticator.os.chmod', side_effect=OSError('permission denied'))
    @patch('tracker.gmail_authenticator.pickle.dump')
    @patch('tracker.gmail_authenticator.open', new_callable=mock_open)
    @patch('tracker.gmail_authenticator.InstalledAppFlow')
    @patch('tracker.gmail_authenticator.build')
    @patch('tracker.gmail_authenticator.os.path.exists')
    def test_authenticate_logs_warning_when_chmod_fails(
        self,
        mock_exists,
        mock_build,
        mock_installed_app_flow,
        mock_file,
        mock_pickle_dump,
        mock_chmod,
        mock_logger_warning,
        mock_etd_handler
    ):
        mock_etd_handler.return_value.get_path.side_effect = lambda filename: f"/tmp/.etd/{filename}"
        mock_exists.side_effect = lambda path: path.endswith('credentials.json')

        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = False
        mock_creds.refresh_token = None

        mock_flow_instance = MagicMock()
        mock_flow_instance.run_local_server.return_value = mock_creds
        mock_installed_app_flow.from_client_secrets_file.return_value = mock_flow_instance

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        authenticator = GmailAuthenticator()
        authenticator.authenticate()

        mock_pickle_dump.assert_called_once_with(mock_creds, mock_file())
        mock_chmod.assert_called_once_with('/tmp/.etd/token.pickle', 0o600)
        mock_logger_warning.assert_called_once()
