import os
import datetime

import unittest
from unittest.mock import patch, MagicMock

from tracker.expense_tracker import ExpenseTracker


class TestExpenseTracker(unittest.TestCase):

    @patch.dict(os.environ, {"ET_SENDER_EMAIL": "test@example.com",
                             "ET_TARGET_SUBJECTS": "Payments confirmation,Top Up Confirmation"})
    def setUp(self):
        """
        Set up an instance of ExpenseTracker for testing with mocked dependencies.
        """
        with patch("tracker.gmail_authenticator.GmailAuthenticator") as MockGmailAuthenticator, \
                patch("tracker.db.SQLiteHandler") as MockSQLiteHandler, \
                patch("tracker.email_fetcher.EmailFetcher") as MockEmailFetcher, \
                patch("tracker.display.Display") as MockDisplay:
            # Mock Gmail Authenticator
            self.mock_service = MagicMock()
            MockGmailAuthenticator().authenticate.return_value = self.mock_service

            # Mock EmailFetcher
            self.mock_email_fetcher = MockEmailFetcher()
            self.mock_email_fetcher.service = self.mock_service

            # Mock SQLiteHandler
            self.mock_db = MockSQLiteHandler()

            # Mock Display
            self.mock_display = MockDisplay()

            # Initialize the ExpenseTracker with mocks
            self.expense_tracker = ExpenseTracker()
            self.expense_tracker.service = self.mock_service
            self.expense_tracker.email_fetcher = self.mock_email_fetcher
            self.expense_tracker.db = self.mock_db
            self.expense_tracker.display = self.mock_display

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
        with self.assertRaises(ValueError) as context:
            ExpenseTracker()
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

        mock_logger_warning.assert_called_once_with(
            "Skipping email with missing data: {'Amount': None}")

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


if __name__ == "__main__":
    unittest.main()
