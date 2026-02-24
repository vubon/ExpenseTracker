import json
import os
import unittest
from datetime import datetime
from unittest.mock import patch

from tracker.email_parser import EmailParser


class TestEmailParser(unittest.TestCase):

    def setUp(self):
        # Mock the environment variable
        custom_rule = {
            "Amount": {"type": "amount"},
            "Note": {"type": "note"},
            "Date": {"type": "date", "format": "%d %B %Y at %H:%M:%S"}
        }
        os.environ['ET_EMAIL_FIELD_RULES'] = json.dumps(custom_rule)

        self.message = {
            'payload': {
                'body': {'data': 'SGVsbG8gd29ybGQ='},  # Base64 encoded "Hello world"
                'parts': []
            }
        }
        self.parser = EmailParser(self.message)

    def test_initialize_email_parser(self):
        self.assertEqual(self.parser.message, "Hello world")
        self.assertEqual(len(self.parser.default_rules), 3)  # Should have 3 default rules
        self.assertEqual(len(self.parser.custom_rules), 3)  # Should have 3 custom rules

    def test_load_rules_from_env(self):
        expected_rules = {
            "Amount": {"type": "amount"},
            "Note": {"type": "note"},
            "Date": {"type": "date", "format": "%d %B %Y at %H:%M:%S"}
        }
        custom_rules = self.parser._load_rules_from_env()
        self.assertEqual(custom_rules, expected_rules)

    def test_process_amount(self):
        raw_value = "Amount $123.45"
        processed_value = self.parser.process_amount(raw_value)
        self.assertEqual(processed_value, 123.45)

    def test_process_date(self):
        raw_value = "01 January 2025 at 12:30:45"
        date_format = "%d %B %Y at %H:%M:%S"
        processed_value = self.parser.process_date(raw_value, date_format)
        self.assertEqual(processed_value, datetime(2025, 1, 1, 12, 30, 45))

    def test_process_default(self):
        raw_value = "   some note text   "
        processed_value = self.parser.process_default(raw_value)
        self.assertEqual(processed_value, "some note text")

    def test_determine_rule_custom(self):
        rule = self.parser.determine_rule("Amount")
        self.assertEqual(rule, self.parser.process_amount)

    def test_determine_rule_default(self):
        rule = self.parser.determine_rule("note")
        self.assertEqual(rule, self.parser.process_note)

    def test_get_field_names(self):
        field_names = self.parser.get_field_names()
        expected_field_names = {"Amount", "Note", "Date"}
        self.assertEqual(field_names, expected_field_names)

    def test_apply_case_function_title_case(self):
        case_func = self.parser._determine_case_function_from_custom_rules()
        self.assertEqual(case_func("Amount"), "Amount")
        self.assertEqual(case_func("note"), "Note")

    def test_apply_case_function_lower_case(self):
        self.parser.custom_rules = {"amount": {"type": "amount"}}
        case_func = self.parser._determine_case_function_from_custom_rules()
        self.assertEqual(case_func("amount"), "amount")

    def test_apply_case_function_upper_case(self):
        self.parser.custom_rules = {"AMOUNT": {"type": "amount"}}
        case_func = self.parser._determine_case_function_from_custom_rules()
        self.assertEqual(case_func("AMOUNT"), "AMOUNT")

    def test_decode_email_body(self):
        raw_message = {
            'payload': {
                'body': {'data': 'SGVsbG8gd29ybGQ='},  # Base64 encoded "Hello world"
                'parts': []
            }
        }
        decoded_message = self.parser.decode_email_body(raw_message)
        self.assertEqual(decoded_message, "Hello world")

    def test_decode_email_multipart_body(self):
        raw_message = {
            'payload': {
                'parts': [{'mimeType': 'text/plain', 'body': {'data': 'SGVsbG8gd29ybGQ='}}]
            }
        }
        decoded_message = self.parser.decode_email_body(raw_message)
        self.assertEqual(decoded_message, "Hello world")

    def test_extract_tags_values_from_body(self):
        html_content = """
               <html>
               <body>
                    <table>
                        <tr>
                            <td>Amount</td>
                            <td>100.50</td>
                        </tr>
                    </table>
               </body>
               </html>
        """
        self.parser.message = html_content
        result = self.parser.extract_tags_values_from_body()

        # This assumes that the field names will be matched and processed correctly.
        self.assertIn('Amount', result)
        self.assertIsInstance(result['Amount'], float)
        self.assertEqual(result['Amount'], 100.50)

    def test_invalid_extract_tags_values_from_body(self):
        html_content = """
               <html>
               <body>
                    <table>
                        <tr>
                            <td>Date</td>
                            <td>10.3K</td>
                        </tr>
                    </table>
               </body>
               </html>
        """
        self.parser.message = html_content
        result = self.parser.extract_tags_values_from_body()

        # This assumes that the field names will be matched and processed correctly.
        self.assertIn('Date', result)
        self.assertIsNone(result['Date'])

    def test_invalid_date_format(self):
        with self.assertRaises(ValueError):
            raw_value = "Invalid Date"
            self.parser.process_date(raw_value)

    def test_invalid_processing_rule(self):
        with self.assertRaises(ValueError):
            self.parser.determine_rule("InvalidField")

    def test_invalid_case_function(self):
        # Test mixed case handling for custom rules
        self.parser.custom_rules = {
            "Amount": {"type": "amount"},
            "Note": {"type": "default"},
            "DATE": {"type": "date"}
        }
        case_func = self.parser._determine_case_function_from_custom_rules()
        self.assertEqual(case_func("Amount"), "Amount")

    def test_invalid_load_rules_from_env(self):
        os.environ['ET_EMAIL_FIELD_RULES'] = 'Hello'
        expected_rules = {}
        custom_rules = self.parser._load_rules_from_env()
        self.assertEqual(custom_rules, expected_rules)

    def test_invalid_custom_rule_field_type(self):
        with self.assertRaises(ValueError):
            self.parser.custom_rules = {"Amount": {"type": "hello"}}
            self.parser.determine_rule("Amount")

    def test_missing_custom_rule_date_format(self):
        with self.assertRaises(ValueError):
            self.parser.custom_rules = {"Date": {"type": "date"}}
            self.parser.determine_rule("Date")

    def test_process_note_multi_word(self):
        raw_value = "Payment completed. Note Family dinner at downtown Date 01 January 2025 at 12:30:45"
        processed_value = self.parser.process_note(raw_value)
        self.assertEqual(processed_value, "family")

    def test_process_note_stops_at_bank_reference(self):
        raw_value = "Note Groceries Bank Reference No. 524071"
        processed_value = self.parser.process_note(raw_value)
        self.assertEqual(processed_value, "groceries")

    @patch('tracker.logs_config.logger.error')
    def test_decode_email_body_invalid_base64(self, mock_logger):
        raw_message = {
            'payload': {
                'body': {'data': '***invalid***'},
                'parts': []
            }
        }
        decoded_message = self.parser.decode_email_body(raw_message)
        self.assertEqual(decoded_message, "")
        mock_logger.assert_called_once()
