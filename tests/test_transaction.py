import unittest
from datetime import datetime

from tracker.transaction import Transaction


class TestTransaction(unittest.TestCase):
    def test_from_parsed_email_valid_data(self):
        payload = {
            "Amount": "100.50",
            "Note": "Groceries",
            "Date": datetime(2025, 1, 6, 20, 8, 10)
        }

        transaction = Transaction.from_parsed_email(payload)

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.category, "groceries")
        self.assertEqual(transaction.amount, 100.5)
        self.assertEqual(transaction.timestamp, datetime(2025, 1, 6, 20, 8, 10))

    def test_from_parsed_email_missing_amount(self):
        payload = {
            "Note": "Groceries",
            "Date": datetime(2025, 1, 6, 20, 8, 10)
        }

        transaction = Transaction.from_parsed_email(payload)
        self.assertIsNone(transaction)

    def test_from_parsed_email_invalid_amount(self):
        payload = {
            "Amount": "ABC",
            "Note": "Groceries",
            "Date": datetime(2025, 1, 6, 20, 8, 10)
        }

        transaction = Transaction.from_parsed_email(payload)
        self.assertIsNone(transaction)

    def test_from_parsed_email_missing_date(self):
        payload = {
            "Amount": "100.50",
            "Note": "Groceries"
        }

        transaction = Transaction.from_parsed_email(payload)
        self.assertIsNone(transaction)

    def test_from_parsed_email_invalid_date_type(self):
        payload = {
            "Amount": "100.50",
            "Note": "Groceries",
            "Date": "2025-01-06T20:08:10"
        }

        transaction = Transaction.from_parsed_email(payload)
        self.assertIsNone(transaction)

    def test_from_parsed_email_defaults_unknown_note(self):
        payload = {
            "Amount": "50",
            "Note": "   ",
            "Date": datetime(2025, 1, 6, 20, 8, 10)
        }

        transaction = Transaction.from_parsed_email(payload)

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.category, "unknown")
