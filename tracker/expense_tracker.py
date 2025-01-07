import datetime
import os
import time

from tracker.logs_config import logger
from tracker.gmail_authenticator import GmailAuthenticator
from tracker.email_fetcher import EmailFetcher
from tracker.email_parser import EmailParser
from tracker.db import SQLiteHandler
from tracker.display import Display

DEFAULT_SUBJECTS = ("Payments confirmation,Confirmation of funds transfer,Top Up Confirmation,\n"
                    "Pay with QR transaction,Confirmation of Cardless Withdrawal ")


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

        self.validate_env_variables()

    def validate_env_variables(self):
        if not self.sender_email:
            logger.error("Missing CC_SENDER_EMAIL. Please set this environment variable.")
            raise ValueError("Missing environment variable: ET_SENDER_EMAIL")

    def run(self):
        try:
            messages = self.email_fetcher.filter_unread_messages(self.sender_email, self.target_subjects)

            if not messages:
                logger.info("No more email")
                return

            for message in messages:
                parser = EmailParser(message=message)
                data = parser.extract_tags_values_from_body()

                if self.process_data(data):
                    self.email_fetcher.mark_message_as_read(message.get("id"))

        except Exception as err:
            logger.error(f"Unknown error: {err}")

    def process_data(self, data):
        amount, note, date = data.get("Amount"), data.get("Note", "unknown"), data.get("Date")

        if any(x is None for x in [amount, date]):
            logger.warning(f"Skipping email with missing data: {data}")
            return False

        # Create a new entry in the database
        return self.db.create(note, amount, date)

    def show(self):
        clear_screen()
        now = datetime.datetime.now()
        res = self.db.generate_monthly_report(now.year, now.month)
        self.display.display_summary(res)

    def close(self):
        self.db.close_connection()


if __name__ == '__main__':
    expense = ExpenseTracker()
    try:
        while True:
            expense.show()
            expense.run()
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Process interrupted. Exiting...")
    finally:
        expense.close()
