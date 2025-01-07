from datetime import datetime
from calendar import monthrange
import sqlite3

from tracker.etd import ETDHandler
from tracker.logs_config import logger


class SQLiteHandler:
    def __init__(self, db_name: str = 'expense_tracker.db'):
        """
        Initialize the SQLiteHandler and create the necessary tables.
        Args:
            db_name (str): Name of the SQLite database file.
        """
        self.ccd_handler = ETDHandler()
        db_path = self.ccd_handler.get_path(db_name)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_table()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection()

    def create_table(self) -> None:
        """
        Create the transaction table and index if they don't exist.
        """
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL
        )
        ''')
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_category ON transactions (category)
        ''')
        self.conn.commit()

    def close_connection(self) -> None:
        """
        Close the database connection.
        """
        self.conn.close()

    def create(self, category: str, amount: float, timestamp: datetime) -> bool:
        """
        Insert a new transaction into the database.
        Args:
            category (str): Transaction category.
            amount (float): Transaction amount.
            timestamp (datetime): Timestamp of the transaction.
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self.cursor.execute('''
                INSERT INTO transactions (timestamp, category, amount)
                VALUES (?, ?, ?)
                ''', (timestamp.isoformat(), category, amount))
            self.conn.commit()
            return True
        except sqlite3.Error as err:
            logger.error(f"Database error: {err}")
            return False

    def generate_daily_report(self, year: int, month: int, day: int) -> list:
        """
        Generate a report of total amounts by category for a specific day.

        Args:
            year (str): Year of the report.
            month (str): Month of the report.
            day (str): Day of the report.

        Returns:
            list: Report data as a list of tuples (category, total).
        """
        start_date = f"{year}-{month:02d}-{day:02d}T00:00:00"
        end_date = f"{year}-{month:02d}-{day:02d}T23:59:59"
        q = "SELECT category, SUM(amount) AS total FROM transactions WHERE timestamp BETWEEN ? AND ? GROUP BY category"
        try:
            self.cursor.execute(q, (start_date, end_date))
            return self.cursor.fetchall()
        except sqlite3.Error as err:
            logger.error(f"Failed to generate daily report: {err}")
            return []

    def generate_monthly_report(self, year: int, month: int) -> list:
        """
        Generate a report of total amounts by category for a given month.
        Args:
            year (int): Year for the report.
            month (int): Month for the report.
        Returns:
            list: Report data as a list of tuples (category, total).
        """
        last_day = monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01T00:00:00"
        end_date = f"{year}-{month:02d}-{last_day:02d}T23:59:59"
        try:
            self.cursor.execute('''
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY category
            ''', (start_date, end_date))
            return self.cursor.fetchall()
        except sqlite3.Error as err:
            logger.error(f"Failed to generate monthly report: {err}")
            return []

    def generate_yearly_report(self, year: int) -> list:
        """
        Generate a report of total amounts by category for a given year.
        Args:
            year (int): Year for the report.
        Returns:
            list: Report data as a list of tuples (category, total).
        """
        start_date = f"{year}-01-01T00:00:00"
        end_date = f"{year}-12-31T23:59:59"
        try:
            self.cursor.execute('''
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY category
            ''', (start_date, end_date))
            return self.cursor.fetchall()
        except sqlite3.Error as err:
            logger.error(f"Failed to generate yearly report: {err}")
            return []
