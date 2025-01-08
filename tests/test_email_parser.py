import os
import unittest
from datetime import datetime

from tracker.email_parser import EmailParser


class TestEmailParser(unittest.TestCase):

    def setUp(self):
        # Mock the environment variable
        os.environ['ET_EMAIL_FIELD_RULES'] = '{"Amount": {"type": "amount"}, "Note": {"type": "default"}}'

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
        self.assertEqual(len(self.parser.custom_rules), 2)  # Should have 2 custom rules

    def test_load_rules_from_env(self):
        expected_rules = {
            "Amount": {"type": "amount"},
            "Note": {"type": "default"}
        }
        custom_rules = self.parser._load_rules_from_env()
        self.assertEqual(custom_rules, expected_rules)

    def test_process_amount(self):
        raw_value = "$123.45"
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
        self.assertEqual(rule, self.parser.process_default)

    def test_get_field_names(self):
        field_names = self.parser.get_field_names()
        expected_field_names = {"Amount", "Note", "Date"}
        self.assertEqual(field_names, expected_field_names)

    def test_apply_case_function_title_case(self):
        case_func = self.parser._determine_case_function_from_custom_rules()
        self.assertEqual(case_func("Amount"), "Amount")
        self.assertEqual(case_func("note"), "Note")

    def test_decode_email_body(self):
        raw_message = {
            'payload': {
                'body': {'data': 'SGVsbG8gd29ybGQ='},  # Base64 encoded "Hello world"
                'parts': []
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

    def test_invalid_date_format(self):
        with self.assertRaises(ValueError):
            raw_value = "Invalid Date"
            self.parser.process_date(raw_value)

    def test_invalid_processing_rule(self):
        with self.assertRaises(ValueError):
            self.parser.determine_rule("InvalidField")

    def test_case_function_error(self):
        # Test mixed case handling for custom rules
        self.parser.custom_rules = {
            "Amount": {"type": "amount"},
            "Note": {"type": "default"},
            "DATE": {"type": "date"}
        }
        with self.assertRaises(ValueError):
            self.parser._determine_case_function_from_custom_rules()
