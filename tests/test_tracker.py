import json
import os
import datetime
from argparse import Namespace

import unittest
from unittest.mock import patch, MagicMock

from tracker.expense_tracker import ExpenseTracker, clear_screen, run_cli, main, run_install
from tracker.email_fetcher import EmailFetchError


class TestExpenseTracker(unittest.TestCase):

    @patch.dict(os.environ, {"ET_SENDER_EMAIL": "test@example.com",
                             "ET_TARGET_SUBJECTS": "Payments confirmation,Top Up Confirmation"})
    def setUp(self):
        """
        Set up an instance of ExpenseTracker for testing with mocked dependencies.
        """
        self.test_dir = '/tmp/etd'
        os.makedirs(self.test_dir, exist_ok=True)

        with patch("tracker.gmail_authenticator.GmailAuthenticator", autospec=True) as MockGmailAuthenticator, \
                patch("tracker.db.SQLiteHandler") as MockSQLiteHandler, \
                patch("tracker.email_fetcher.EmailFetcher") as MockEmailFetcher, \
                patch("tracker.display.Display") as MockDisplay, \
                patch("tracker.gmail_authenticator.ETDHandler") as mockETD, \
                patch.object(ExpenseTracker, '__init__', lambda x: None):

            # Mock Gmail Authenticator
            self.mock_etd_handler = mockETD.return_value
            # self.mock_etd_handler.get_path.return_value = self.test_dir
            self.mock_etd_handler.get_path.side_effect = lambda filename: os.path.join(self.test_dir, filename)
            self.mock_service = MagicMock()
            self.mock_gmail = MockGmailAuthenticator.return_value
            self.mock_gmail.authenticate.return_value = self.mock_service

            # Mock EmailFetcher
            self.mock_email_fetcher = MockEmailFetcher()
            self.mock_email_fetcher.service = self.mock_service

            # Mock SQLiteHandler
            self.mock_db = MockSQLiteHandler()

            # Mock Display
            self.mock_display = MockDisplay()

            # Initialize the ExpenseTracker with mocks
            self.expense_tracker = ExpenseTracker()
            self.expense_tracker.gmail = self.mock_gmail
            self.expense_tracker.service = self.mock_service
            self.expense_tracker.email_fetcher = self.mock_email_fetcher
            self.expense_tracker.db = self.mock_db
            self.expense_tracker.display = self.mock_display
            self.expense_tracker.sender_email = os.environ.get("ET_SENDER_EMAIL")
            self.expense_tracker.target_subjects = os.environ.get("ET_TARGET_SUBJECTS")

    def test_validate_env_variables_success(self):
        """
        Test that environment variable validation passes when variables are set.
        """
        self.assertEqual(self.expense_tracker.sender_email, "test@example.com")
        self.assertIn("Payments confirmation", self.expense_tracker.target_subjects)

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_env_variables_failure(self):
        """
        Test that an error is raised when environment variables are missing.
        """
        self.expense_tracker.sender_email = None
        with self.assertRaises(ValueError) as context:
            self.expense_tracker.validate_env_variables()
        self.assertEqual(str(context.exception), "Missing environment variable: ET_SENDER_EMAIL")

    @patch("tracker.logs_config.logger.info")
    def test_run_no_messages(self, mock_logger_info):
        """
        Test that the `run` method handles no unread messages correctly.
        """
        self.mock_email_fetcher.filter_unread_messages.return_value = []
        self.expense_tracker.run()
        mock_logger_info.assert_called_with("No more email")

    @patch("tracker.email_parser.EmailParser")
    @patch("tracker.logs_config.logger.warning")
    def test_run_skips_invalid_data(self, mock_logger_warning, mock_email_parser):
        """
        Test that the `run` method skips processing emails with invalid data.
        """
        # Mock the `list` method and its chained `.execute()`
        mock_list = self.mock_service.users().messages().list
        mock_execute = mock_list.return_value.execute
        mock_execute.return_value = {'messages': [{'id': '123'}]}

        self.mock_email_fetcher.list_unread_messages.return_value = [{"id": "123"}]
        self.mock_email_fetcher.filter_unread_messages.return_value = [{
            'id': '123',
            'payload': {
                'body': {'data': 'PGh0bWw+CiAgIDxib2R5PgogICAgICA8dGFibGU+CiAgICAgICAgIDx0cj4KICAgICAgICAgICAgPHRkPkFtb\
                3VudDwvdGQ+CiAgICAgICAgICAgIDx0ZD5UZXN0PC90ZD4KICAgICAgICAgPC90cj4KICAgICAgPC90YWJsZT4KICAgPC9ib2R5Pgo8\
                L2h0bWw+'},
                'parts': []
            }
        }]

        mock_email_parser().extract_tags_values_from_body.return_value = {"Amount": None}
        self.expense_tracker.run()

        # Capture the actual log message
        mock_logger_warning.assert_called_once()
        actual_log_message = mock_logger_warning.call_args[0][0]

        # Extract dictionary part from the string (after the colon)
        actual_data_str = actual_log_message.split(": ", 1)[1]
        actual_data = json.loads(actual_data_str.replace("'", '"').replace("None", "null"))

        # Define expected dictionary
        expected_data = {'Date': None, 'Note': 'unknown', 'Amount': None}

        assert actual_data == expected_data, f"Expected {expected_data}, but got {actual_data}"

    @patch("tracker.email_parser.EmailParser")
    def test_run_processes_valid_emails(self, mock_email_parser):
        """
        Test that the `run` method processes emails with valid data.
        """
        # Mock the `list` method and its chained `.execute()`
        mock_list = self.mock_service.users().messages().list
        mock_execute = mock_list.return_value.execute
        mock_execute.return_value = {'messages': [{'id': '123'}]}

        self.mock_email_fetcher.list_unread_messages.return_value = [{"id": "123"}]
        self.mock_email_fetcher.filter_unread_messages.return_value = [{
            'id': '123',
            'payload': {
                'body': {
                    'data': 'PGh0bWw+CiAgIDxib2R5PgogICAgICA8dGFibGU+CiAgICAgICAgIDx0cj4KICAgICAgICAgICAgPHRkPkFtb3VudD\
                    wvdGQ+CiAgICAgICAgICAgIDx0ZD4xMDAuNTA8L3RkPgogICAgICAgICA8L3RyPgogICAgICAgICA8dHI+CiAgICAgICAgICAgID\
                    x0ZD5EYXRlPC90ZD4KICAgICAgICAgICAgPHRkPjYgSmFudWFyeSAyMDI1IGF0IDIwOjA4OjEwPC90ZD4KICAgICAgICAgPC90cj\
                    4KICAgICAgPC90YWJsZT4KICAgPC9ib2R5Pgo8L2h0bWw+'},
                'parts': []
            }
        }]

        mock_email_parser().extract_tags_values_from_body.return_value = {
            "Amount": 100.5, "Note": "unknown", "Date": datetime.datetime(2025, 1, 6, 20, 8, 10)
        }
        self.mock_db.create.return_value = True

        self.expense_tracker.run()

        self.mock_db.create.assert_called_once_with("unknown", 100.5, datetime.datetime(2025, 1, 6, 20, 8, 10))
        self.mock_email_fetcher.mark_message_as_read.assert_called_once_with("123")

    @patch("tracker.logs_config.logger.error")
    def test_run_handle_unknown_exception(self, mock_logger):
        self.expense_tracker.email_fetcher.filter_unread_messages = MagicMock(side_effect=Exception("Test exception"))
        self.expense_tracker.run()
        self.expense_tracker.email_fetcher.filter_unread_messages.assert_called_once_with(
            self.expense_tracker.sender_email, self.expense_tracker.target_subjects
        )
        mock_logger.assert_called_once_with("Unknown error: Test exception")

    @patch("tracker.logs_config.logger.error")
    def test_run_handle_email_fetch_error(self, mock_logger):
        self.expense_tracker.email_fetcher.filter_unread_messages = MagicMock(
            side_effect=EmailFetchError("gmail failure")
        )

        self.expense_tracker.run()

        self.expense_tracker.email_fetcher.filter_unread_messages.assert_called_once_with(
            self.expense_tracker.sender_email, self.expense_tracker.target_subjects
        )
        mock_logger.assert_called_once_with("Email fetch failed: gmail failure")

    @patch("tracker.expense_tracker.clear_screen")
    def test_show_calls_display(self, mock_clear_screen):
        """
        Test that the `show` method clears the screen and calls the display function.
        """
        # Mock database report generation
        self.mock_db.generate_monthly_report.return_value = [("Food", 150.0), ("Transport", 50.0)]

        # Call the show method
        self.expense_tracker.show()

        # Assert the methods were called
        mock_clear_screen.assert_called_once()

    def test_close_calls_db_close(self):
        """
        Test that the `close` method closes the database connection.
        """
        self.expense_tracker.close()

        # Assert that the close_connection method was called once
        self.mock_db.close_connection.assert_called_once()

    def tearDown(self):
        """
        Clean up after each test.
        """
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)


class TestClearScreen(unittest.TestCase):
    @patch('os.system')  # Mock `os.system` to prevent actual terminal clearing
    def test_clear_screen_posix(self, mock_os_system):
        """
        Test `clear_screen` for POSIX systems (e.g., Linux, macOS).
        """
        with patch('os.name', 'posix'):  # Simulate POSIX system
            clear_screen()
            # Check that `os.system` is called with 'clear'
            mock_os_system.assert_called_once_with('clear')

        # Ensure TERM is set to `xterm-256color`
        self.assertEqual(os.environ['TERM'], 'xterm-256color')


class TestCLIFlow(unittest.TestCase):
    @patch("builtins.print")
    @patch("tracker.expense_tracker.InstallationManager")
    def test_run_install_handles_keyboard_interrupt(self, mock_installer_cls, mock_print):
        mock_installer = mock_installer_cls.return_value
        mock_installer.is_installed.return_value = False
        mock_installer.run.side_effect = KeyboardInterrupt

        run_install()

        mock_print.assert_any_call("\nInstallation cancelled.")

    @patch("tracker.expense_tracker.run_continuous")
    @patch("tracker.expense_tracker.run_install")
    def test_run_cli_install_command(self, mock_run_install, mock_run_continuous):
        args = Namespace(command="install")
        run_cli(args)
        mock_run_install.assert_called_once_with()
        mock_run_continuous.assert_not_called()

    @patch("tracker.expense_tracker.run_continuous")
    def test_run_cli_continuous_with_interval(self, mock_run_continuous):
        args = Namespace(interval=15)
        run_cli(args)
        mock_run_continuous.assert_called_once_with(15)

    @patch("tracker.expense_tracker.run_continuous")
    def test_run_cli_continuous_without_interval(self, mock_run_continuous):
        args = Namespace()
        run_cli(args)
        mock_run_continuous.assert_called_once_with()

    @patch("tracker.expense_tracker.run_monthly_summary")
    def test_run_cli_monthly(self, mock_run_monthly_summary):
        args = Namespace(month=2, year=2025)
        run_cli(args)
        mock_run_monthly_summary.assert_called_once_with(2, 2025)

    def test_run_cli_invalid_combination_calls_parser_error(self):
        parser = MagicMock()
        parser.error.side_effect = SystemExit(2)

        with self.assertRaises(SystemExit):
            run_cli(Namespace(month=2), parser)

        parser.error.assert_called_once_with("Both --month and --year are required together.")

    @patch("tracker.expense_tracker.run_cli")
    def test_main_parses_args_and_delegates(self, mock_run_cli):
        main(["--month", "2", "--year", "2025"])
        called_args = mock_run_cli.call_args[0][0]
        self.assertEqual(called_args.month, 2)
        self.assertEqual(called_args.year, 2025)

    @patch('os.system')  # Mock `os.system` to prevent actual terminal clearing
    def test_clear_screen_non_posix(self, mock_os_system):
        """
        Test `clear_screen` for non-POSIX systems (e.g., Windows).
        """
        with patch('os.name', 'nt'):  # Simulate non-POSIX system (Windows)
            clear_screen()
            # Check that `os.system` is called with 'cls'
            mock_os_system.assert_called_once_with('cls')

        # Ensure TERM is set to `xterm-256color`
        self.assertEqual(os.environ['TERM'], 'xterm-256color')
