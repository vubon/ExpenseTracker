from datetime import datetime
from calendar import monthrange
import sqlite3

from tracker.etd import ETDHandler
from tracker.logs_config import logger


CURRENT_SCHEMA_VERSION = 1


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
        self.initialize_database()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection()

    def initialize_database(self) -> None:
        self.create_schema_version_table()
        current_version = self.get_schema_version()
        self.apply_migrations(current_version)

    def create_schema_version_table(self) -> None:
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        )
        ''')
        self.conn.commit()

    def get_schema_version(self) -> int:
        self.cursor.execute('SELECT version FROM schema_version LIMIT 1')
        row = self.cursor.fetchone()
        return int(row[0]) if row else 0

    def set_schema_version(self, version: int) -> None:
        self.cursor.execute('DELETE FROM schema_version')
        self.cursor.execute('INSERT INTO schema_version (version) VALUES (?)', (version,))
        self.conn.commit()

    def apply_migrations(self, current_version: int) -> None:
        migrations = {
            1: self._migration_1_create_transactions_table
        }

        version = current_version
        while version < CURRENT_SCHEMA_VERSION:
            next_version = version + 1
            migration = migrations.get(next_version)
            if migration is None:
                raise RuntimeError(f"Missing migration for schema version {next_version}")

            migration()
            self.set_schema_version(next_version)
            version = next_version

    def _migration_1_create_transactions_table(self) -> None:
        self.create_table()

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
