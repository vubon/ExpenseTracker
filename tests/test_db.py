import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from tracker.db import SQLiteHandler


class TestSQLiteHandler(unittest.TestCase):
    def setUp(self):
        # Mock sqlite3 connection and cursor
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Patch sqlite3.connect to return the mock connection
        self.sqlite_connect_patch = patch('sqlite3.connect', return_value=self.mock_conn)
        self.sqlite_connect_patch.start()

        # Initialize SQLiteHandler with mock connection
        self.db_handler = SQLiteHandler(db_name=':memory:')

    def tearDown(self):
        self.sqlite_connect_patch.stop()

    def test_create_table(self):
        # Verify create_table executes the expected SQL commands
        self.db_handler.create_table()
        self.mock_cursor.execute.assert_any_call('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL
        )
        ''')
        self.mock_cursor.execute.assert_any_call('''
        CREATE INDEX IF NOT EXISTS idx_category ON transactions (category)
        ''')

    def test_create_transaction(self):
        # Test inserting a transaction
        self.mock_cursor.execute.return_value = None
        success = self.db_handler.create(
            category="Food",
            amount=25.50,
            timestamp=datetime(2025, 1, 1, 12, 0)
        )
        self.assertTrue(success)
        self.mock_cursor.execute.assert_called_with('''
                INSERT INTO transactions (timestamp, category, amount)
                VALUES (?, ?, ?)
                ''', ('2025-01-01T12:00:00', 'Food', 25.50))

    def test_generate_daily_report(self):
        # Mock cursor fetchall to return fake data
        self.mock_cursor.fetchall.return_value = [('Food', 50.00)]
        report = self.db_handler.generate_daily_report(year=2025, month=1, day=1)

        # Normalize the expected query string by stripping extra whitespace
        q = "SELECT category, SUM(amount) AS total FROM transactions WHERE timestamp BETWEEN ? AND ? GROUP BY category"

        # Get the actual query from the call arguments and strip extra whitespace
        actual_query = self.mock_cursor.execute.call_args[0][0]
        self.assertEqual(actual_query, q)

        # Also check the parameters passed to execute
        self.mock_cursor.execute.assert_any_call(q, ('2025-01-01T00:00:00', '2025-01-01T23:59:59'))

        # Check if the report generated is correct
        self.assertEqual(report, [('Food', 50.00)])

    def test_generate_monthly_report(self):
        # Mock cursor fetchall to return fake data
        self.mock_cursor.fetchall.return_value = [('Food', 50.00)]
        report = self.db_handler.generate_monthly_report(year=2025, month=1)

        self.mock_cursor.execute.assert_any_call('''
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY category
            ''', ('2025-01-01T00:00:00', '2025-01-31T23:59:59'))
        self.assertEqual(report, [('Food', 50.00)])

    def test_generate_yearly_report(self):
        # Mock cursor fetchall to return fake data
        self.mock_cursor.fetchall.return_value = [('Food', 600.00)]
        report = self.db_handler.generate_yearly_report(year=2025)
        # Allow for multiple calls to execute (e.g., due to timestamp conversion or other logic)
        self.mock_cursor.execute.assert_any_call('''
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY category
            ''', ('2025-01-01T00:00:00', '2025-12-31T23:59:59'))
        self.assertEqual(report, [('Food', 600.00)])


if __name__ == '__main__':
    unittest.main()
