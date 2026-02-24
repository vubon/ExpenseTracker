import argparse
import datetime
import os
import time

from tracker.validators import validate_month_year, validate_args, validate_sender_email
from tracker.logs_config import logger
from tracker.gmail_authenticator import GmailAuthenticator
from tracker.email_fetcher import EmailFetcher, EmailFetchError
from tracker.email_parser import EmailParser
from tracker.db import SQLiteHandler
from tracker.display import Display
from tracker.transaction import Transaction

DEFAULT_SUBJECTS = "Payments,funds transfer,Top Up,QR transaction,Cardless Withdrawal,Funds transfer"


def clear_screen():
    """
    Clear the terminal screen.

    This function detects the operating system and clears the screen accordingly.
    """
    os.environ['TERM'] = 'xterm-256color'
    os.system('clear' if os.name == 'posix' else 'cls')


class ExpenseTracker:

    def __init__(self):
        self.gmail = GmailAuthenticator()
        self.service = self.gmail.authenticate()
        self.db = SQLiteHandler()
        self.email_fetcher = EmailFetcher(service=self.service)
        self.display = Display()
        self.sender_email = os.getenv("ET_SENDER_EMAIL")
        self.target_subjects = os.getenv("ET_TARGET_SUBJECTS", DEFAULT_SUBJECTS).split(",")

    def validate_env_variables(self):
        if not self.sender_email:
            logger.error("Missing ET_SENDER_EMAIL. Please set this environment variable.")
            raise ValueError("Missing environment variable: ET_SENDER_EMAIL")

    @validate_sender_email
    def run(self):
        try:
            messages = self.email_fetcher.filter_unread_messages(self.sender_email, self.target_subjects)
        except EmailFetchError as err:
            logger.error(f"Email fetch failed: {err}")
            return
        except Exception as err:
            logger.error(f"Unknown error: {err}")
            return

        if not messages:
            logger.info("No more email")
            return

        for message in messages:
            try:
                email_parser = EmailParser(message=message)
                data = email_parser.extract_tags_values_from_body()

                if self.process_data(data):
                    mark_as_read_result = self.email_fetcher.mark_message_as_read(message.get("id"))
                    if mark_as_read_result is False:
                        logger.warning(f"Processed message but failed to mark as read: {message.get('id')}")
            except ValueError as err:
                logger.warning(f"Skipping email due to parsing error: {err}")
            except Exception as err:
                logger.error(f"Failed to process message {message.get('id')}: {err}")

    def process_data(self, data):
        transaction = Transaction.from_parsed_email(data)

        if transaction is None:
            logger.warning(f"Skipping email with missing data: {data}")
            return False

        # Create a new entry in the database
        return self.db.create(transaction.category, transaction.amount, transaction.timestamp)

    def show(self):
        clear_screen()
        now = datetime.datetime.now()
        res = self.db.generate_monthly_report(now.year, now.month)
        self.display.display_summary(res)

    @validate_month_year
    def get_monthly_summary(self, month, year) -> None:
        self.display.display_summary(self.db.generate_monthly_report(year, month))

    def close(self):
        self.db.close_connection()


def run_continuous(interval: int = 3600):
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


def run_monthly_summary(month, year):
    expense = ExpenseTracker()
    try:
        expense.get_monthly_summary(month, year)
    except Exception as err:
        logger.error(f"Error generating summary: {err}")
    finally:
        expense.close()


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Expense Tracker CLI")
    parser.add_argument('--interval', type=int, help='Run continuously every N seconds', default=argparse.SUPPRESS)
    parser.add_argument('--month', type=int, help='Month for summary (1–12)', default=argparse.SUPPRESS)
    parser.add_argument('--year', type=int, help='Year for summary (e.g., 2024)', default=argparse.SUPPRESS)
    return parser


def run_cli(args, parser: argparse.ArgumentParser | None = None) -> None:
    parser = parser or create_parser()
    mode, error = validate_args(args)

    if mode == "error":
        parser.error(error or "Invalid combination of arguments.")
    elif mode == "continuous":
        run_continuous(args.interval) if hasattr(args, "interval") else run_continuous()
    elif mode == "monthly":
        run_monthly_summary(args.month, args.year)


def main(argv=None) -> None:
    parser = create_parser()
    args = parser.parse_args(argv)
    run_cli(args, parser)


if __name__ == '__main__':
    main()
