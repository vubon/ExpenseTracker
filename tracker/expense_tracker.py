import argparse
import datetime
import os
import sqlite3 # Added import
import time

from googleapiclient.errors import HttpError # Added import
from tracker.validators import validate_month_year, validate_args, validate_sender_email
from tracker.logs_config import logger
from tracker.gmail_authenticator import GmailAuthenticator
from tracker.email_fetcher import EmailFetcher
from tracker.email_parser import EmailParser
from tracker.db import SQLiteHandler
from tracker.display import Display

DEFAULT_SUBJECTS = "Payments,funds transfer,Top Up,QR transaction,Cardless Withdrawal,Funds transfer"
"""
str: A comma-separated string of default email subjects to filter for.
This is used if the `ET_TARGET_SUBJECTS` environment variable is not set.
It helps in identifying emails that are likely to be transaction notifications.
"""


def clear_screen():
    """Clears the terminal screen.

    This function checks the operating system and uses the appropriate
    command ('clear' for POSIX, 'cls' for Windows) to clear the screen.
    It also sets the TERM environment variable to 'xterm-256color'
    for better compatibility with some terminal features.
    """
    os.environ['TERM'] = 'xterm-256color'
    os.system('clear' if os.name == 'posix' else 'cls')


class ExpenseTracker:
    """Manages fetching, processing, and displaying expense data from emails."""

    def __init__(self):
        """Initializes the ExpenseTracker.

        Sets up authentication with Gmail, initializes the database handler,
        email fetcher, and display handler. It also loads necessary
        environment variables for sender email and target subjects.

        Attributes:
            gmail (GmailAuthenticator): Instance for handling Gmail authentication.
            service: Authenticated Gmail API service instance.
            db (SQLiteHandler): Instance for database operations.
            email_fetcher (EmailFetcher): Instance for fetching emails.
            display (Display): Instance for displaying data.
            sender_email (str | None): The sender email address to filter emails from,
                loaded from the `ET_SENDER_EMAIL` environment variable.
            target_subjects (list[str]): A list of target email subjects to filter for,
                loaded from `ET_TARGET_SUBJECTS` or `DEFAULT_SUBJECTS`.
        """
        self.gmail = GmailAuthenticator()
        self.service = self.gmail.authenticate()
        self.db = SQLiteHandler()
        self.email_fetcher = EmailFetcher(service=self.service)
        self.display = Display()
        self.sender_email = os.getenv("ET_SENDER_EMAIL")
        self.target_subjects = os.getenv("ET_TARGET_SUBJECTS", DEFAULT_SUBJECTS).split(",")

    def validate_env_variables(self):
        """Validates that required environment variables are set.

        Currently checks for `ET_SENDER_EMAIL`.

        Raises:
            ValueError: If `ET_SENDER_EMAIL` is not set.
        """
        if not self.sender_email:
            logger.error("Missing ET_SENDER_EMAIL. Please set this environment variable.")
            raise ValueError("Missing environment variable: ET_SENDER_EMAIL")

    @validate_sender_email
    def run(self):
        """Fetches unread emails, processes them, and stores transaction data.

        - Validates environment variables.
        - Filters unread messages based on sender and subject.
        - Parses each email to extract transaction data (amount, note, date).
        - Processes valid data and stores it in the database.
        - Marks processed emails as read.

        Handles potential errors during the process and logs them.
        The `@validate_sender_email` decorator ensures `sender_email` is valid
        before this method runs.
        """
        try:
            self.validate_env_variables() # Ensure this is called if not implicitly by decorator

            try:
                messages = self.email_fetcher.filter_unread_messages(self.sender_email, self.target_subjects)
            except HttpError as e:
                logger.error(f"Gmail API error while fetching messages: {e}")
                return # Stop further processing in run() if fetching fails

            if not messages:
                logger.info("No new emails to process.")
                return

            for message_data in messages: # Renamed to avoid confusion with outer message variable
                message_id = message_data.get("id")
                try:
                    # EmailParser initialization and data extraction can raise ValueErrors (e.g. from date parsing)
                    email_parser = EmailParser(message=message_data)
                    data = email_parser.extract_tags_values_from_body()

                    if self.process_data(data): # This calls db.create, which logs sqlite3.Error and returns False
                        try:
                            self.email_fetcher.mark_message_as_read(message_id)
                        except HttpError as e:
                            logger.error(f"Gmail API error while marking message {message_id} as read: {e}")
                            # Continue processing other messages even if one fails to be marked as read
                    else:
                        # process_data returning False means data was invalid or db.create failed.
                        # db.create logs its own sqlite3.Error.
                        # process_data logs warnings for invalid data.
                        logger.warning(f"Failed to process or store data for message ID {message_id}. See previous logs for details.")

                except ValueError as e:
                    logger.error(f"ValueError processing message ID {message_id}: {e}. Raw data: {data if 'data' in locals() else 'N/A'}")
                except Exception as e: # Catch other unexpected errors during single message processing
                    logger.error(f"Unexpected error processing message ID {message_id}: {e}")

        except ValueError as e: # Catches ValueError from validate_env_variables
            logger.error(f"Configuration error in ExpenseTracker.run: {e}")
        except Exception as err: # General catch-all for other unexpected errors in run method
            logger.error(f"An unexpected error occurred in ExpenseTracker.run method: {err}")

    def process_data(self, data: dict) -> bool:
        """Processes extracted email data and stores it in the database.

        Args:
            data (dict): A dictionary containing extracted transaction details.
                Expected keys are "Amount", "Note" (optional, defaults to "unknown"),
                and "Date".

        Returns:
            bool: True if the data was successfully processed and stored,
                  False otherwise (e.g., if essential data like amount or date
                  is missing).
        """
        amount, note, date = data.get("Amount"), data.get("Note", "unknown"), data.get("Date")

        if any(x is None for x in [amount, date]):
            logger.warning(f"Skipping email with missing data: {data}")
            return False

        # Create a new entry in the database
        return self.db.create(note, amount, date)

    def show(self):
        """Clears the screen and displays the current month's summary report."""
        clear_screen()
        now = datetime.datetime.now()
        res = self.db.generate_monthly_report(now.year, now.month)
        self.display.display_summary(res)

    @validate_month_year
    def get_monthly_summary(self, month: int, year: int) -> None:
        """Displays a summary report for the specified month and year.

        The `@validate_month_year` decorator ensures month and year are valid
        before this method runs.

        Args:
            month (int): The month for the summary (1-12).
            year (int): The year for the summary.
        """
        self.display.display_summary(self.db.generate_monthly_report(year, month))

    def close(self):
        """Closes the database connection."""
        self.db.close_connection()


def run_continuous(interval: int = 3600):
    """Runs the expense tracker continuously, checking for new emails periodically.

    Initializes an `ExpenseTracker` instance. In an infinite loop:
    1. Displays the current month's summary.
    2. Fetches and processes new emails.
    3. Waits for the specified `interval` in seconds.
    4. Displays the summary again.

    The loop can be interrupted with a KeyboardInterrupt (Ctrl+C).
    Ensures the database connection is closed on exit.

    Args:
        interval (int, optional): The time interval in seconds between
            checking for new emails. Defaults to 3600 seconds (1 hour).
    """
    expense = ExpenseTracker()
    try:
        while True:
            expense.show()
            expense.run()
            time.sleep(interval)  # An hour
            expense.show()  # Show the summary again
    except KeyboardInterrupt:
        logger.info("Process interrupted. Exiting...")
    finally:
        expense.close()


def run_monthly_summary(month: int, year: int):
    """Generates and displays a monthly expense summary for the given month and year.

    Initializes an `ExpenseTracker` instance, calls `get_monthly_summary`
    to display the report, and handles potential errors.
    Ensures the database connection is closed on exit.

    Args:
        month (int): The month for the summary (1-12).
        year (int): The year for the summary (e.g., 2024).
    """
    expense = ExpenseTracker()
    try:
        expense.get_monthly_summary(month, year)
    except sqlite3.Error as e:
        logger.error(f"Failed to generate monthly summary for {month}/{year} due to a database error: {e}")
    except Exception as err:
        logger.error(f"An error occurred while generating the monthly summary for {month}/{year}: {err}")
    finally:
        expense.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Expense Tracker CLI")
    parser.add_argument('--interval', type=int, help='Run continuously every N seconds', default=argparse.SUPPRESS)
    parser.add_argument('--month', type=int, help='Month for summary (1–12)', default=argparse.SUPPRESS)
    parser.add_argument('--year', type=int, help='Year for summary (e.g., 2024)', default=argparse.SUPPRESS)

    args = parser.parse_args()
    mode, error = validate_args(args)

    if mode == "continuous":
        run_continuous(args.interval) if hasattr(args, "interval") else run_continuous()
    elif mode == "monthly":
        run_monthly_summary(args.month, args.year)
    else:
        parser.error("Invalid combination of arguments. Use --interval or --month and --year.")
