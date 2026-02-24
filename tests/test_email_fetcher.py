import unittest
from unittest.mock import MagicMock, patch
from tracker.email_fetcher import EmailFetcher, EmailFetchError


class TestEmailFetcher(unittest.TestCase):

    def setUp(self):
        self.mock_service = MagicMock()
        self.email_fetcher = EmailFetcher(service=self.mock_service)

    def test_list_unread_messages(self):
        # Mock the `list` method and its chained `.execute()`
        mock_list = self.mock_service.users().messages().list
        mock_execute = mock_list.return_value.execute
        mock_execute.return_value = {'messages': [{'id': '123'}, {'id': '456'}]}

        # Call the method
        result = self.email_fetcher.list_unread_messages(sender='test@example.com')

        # Assert the correct calls
        mock_list.assert_called_once_with(userId='me', q='from:test@example.com is:unread')
        mock_execute.assert_called_once()

        # Assert the results
        self.assertEqual(result, [{'id': '123'}, {'id': '456'}])

    def test_list_unread_messages_no_messages(self):
        # Mock the response from the Gmail API
        self.mock_service.users().messages().list().execute.return_value = {}

        result = self.email_fetcher.list_unread_messages(sender='test@example.com')
        self.assertEqual(result, [])

    def test_list_unread_messages_raises_email_fetch_error(self):
        self.mock_service.users().messages().list().execute.side_effect = Exception("API Error")

        with self.assertRaises(EmailFetchError) as context:
            self.email_fetcher.list_unread_messages(sender='test@example.com')

        self.assertIn("Unexpected error while listing unread messages", str(context.exception))

    def test_get_message_details(self):
        # Mock the `get` and `execute` methods
        mock_get = self.mock_service.users().messages().get
        mock_execute = mock_get.return_value.execute
        mock_execute.return_value = {'id': '123', 'payload': {}}

        result = self.email_fetcher.get_message_details(message_id='123')

        # Assert the correct calls
        mock_get.assert_called_once_with(userId='me', id='123')
        mock_execute.assert_called_once()  # Ensure `.execute()` is called exactly once
        self.assertEqual(result, {'id': '123', 'payload': {}})

    @patch('tracker.logs_config.logger.error')
    def test_get_message_details_error(self, mock_logger):
        # Mock an exception during Gmail API call
        self.mock_service.users().messages().get().execute.side_effect = Exception('API Error')

        result = self.email_fetcher.get_message_details(message_id='123')
        self.assertIsNone(result)
        mock_logger.assert_called_once_with("Failed to fetch details for message ID 123: API Error")

    def test_mark_message_as_read(self):
        result = self.email_fetcher.mark_message_as_read(message_id='123')
        self.mock_service.users().messages().modify.assert_called_once_with(
            userId='me',
            id='123',
            body={'removeLabelIds': ['UNREAD']}
        )
        self.assertTrue(result)

    def test_mark_message_as_read_no_id(self):
        result = self.email_fetcher.mark_message_as_read(message_id=None)
        self.mock_service.users().messages().modify.assert_not_called()
        self.assertIsNone(result)

    @patch('tracker.logs_config.logger.error')
    def test_mark_message_as_read_error(self, mock_logger):
        self.mock_service.users().messages().modify().execute.side_effect = Exception('API Error')

        result = self.email_fetcher.mark_message_as_read(message_id='123')

        self.assertFalse(result)
        mock_logger.assert_called_once_with("Failed to mark message as read for ID 123: API Error")

    def test_get_email_subject(self):
        message = {
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject'}
                ]
            }
        }
        result = self.email_fetcher.get_email_subject(message)
        self.assertEqual(result, 'Test Subject')

    def test_get_email_subject_no_subject(self):
        message = {'payload': {'headers': [{'name': 'From', 'value': 'test@example.com'}]}}
        result = self.email_fetcher.get_email_subject(message)
        self.assertIsNone(result)

    def test_is_target_subject_match(self):
        message = {
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Payment Received'}
                ]
            }
        }
        result = self.email_fetcher.is_target_subject(
            target_subjects=['Payment'], message=message)
        self.assertTrue(result)

    def test_is_target_subject_no_match(self):
        message = {
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Welcome Email'}
                ]
            }
        }
        result = self.email_fetcher.is_target_subject(
            target_subjects=['Payment'], message=message)
        self.assertFalse(result)

    def test_is_target_subject_no_subject(self):
        message = {
            'payload': {
                'headers': []
            }
        }
        result = self.email_fetcher.is_target_subject(
            target_subjects=['Payment'], message=message)
        self.assertFalse(result)

    @patch('tracker.logs_config.logger.info')
    def test_filter_unread_messages_no_messages(self, mock_logger):
        self.email_fetcher.list_unread_messages = MagicMock(return_value=[])
        result = self.email_fetcher.filter_unread_messages(sender='test@example.com', target_subjects=['Payment'])
        self.assertEqual(result, [])
        mock_logger.assert_called_once_with("No more emails")

    def test_filter_unread_messages_with_matching_subject(self):
        self.email_fetcher.list_unread_messages = MagicMock(return_value=[{'id': '123'}])
        self.email_fetcher.get_message_details = MagicMock(return_value={
            'payload': {
                'headers': [{'name': 'Subject', 'value': 'Payment Received'}]
            }
        })
        self.email_fetcher.is_target_subject = MagicMock(return_value=True)

        result = self.email_fetcher.filter_unread_messages(sender='test@example.com', target_subjects=['Payment'])
        self.assertEqual(result, [{
            'payload': {
                'headers': [{'name': 'Subject', 'value': 'Payment Received'}]
            }
        }])

    def test_filter_unread_messages_no_matching_subject(self):
        self.email_fetcher.list_unread_messages = MagicMock(return_value=[{'id': '123'}])
        self.email_fetcher.get_message_details = MagicMock(return_value={
            'payload': {
                'headers': [{'name': 'Subject', 'value': 'Welcome Email'}]
            }
        })
        self.email_fetcher.is_target_subject = MagicMock(return_value=False)

        result = self.email_fetcher.filter_unread_messages(sender='test@example.com', target_subjects=['Payment'])
        self.assertEqual(result, [])
