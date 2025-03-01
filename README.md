# Expense Tracker

Expense Tracker is a Python-based application that fetches transaction-related emails, processes the data, 
and stores it in an SQLite database for generating reports. It helps track expenses efficiently by categorizing 
transactions and summarizing them in daily, monthly, and yearly reports.

## Features

- **OAuth Authentication**: Securely access Gmail using OAuth2.
- **Email Fetching**: Fetch unread emails from Gmail based on specific subjects & specific email.
- **Data Parsing**: Extract transaction details such as amount, date, and note from email content.
- **Database Storage**: Store transaction data in an SQLite database with indexing for faster queries.
- **Reporting**:
  - Daily, monthly, and yearly transaction summaries.
  - Total expense calculation per category.
- **Display**: Generate reports in a tabular format using the `tabulate` library.
- **Environment Variables**: Securely configure sensitive data like email credentials and target subjects.

## Project Structure

```
ExpenseTracker/
├── tracker/
   ├── __init__.py
   ├── __version__.py        # Version 
   ├── expense_tracker.py    # Main application script
   ├── db.py                 # SQLiteHandler for database interactions
   ├── email_fetcher.py      # Handles email fetching from Gmail
   ├── email_parser.py       # Parses email content
   ├── etd.py                # Directory looker 
   ├── logs_config.py        # Logging configuration
   ├── display.py            # Handles data display
   ├── gmail_authenticator.py # Gmail OAuth authentication
├── tests/                # Unit tests for the application
   │   ├── __init__.py
   │   ├── test_db.py
   │   ├── test_display.py
   │   ├── test_email_fetcher.py
   │   ├── test_email_parser.py
   │   ├── test_etd.py
   │   └── test_tracker.py
   │   
└── README.md             # Project documentation
```

## Prerequisites

- Python 3.8+
- Gmail account with API access enabled
- Google Cloud project with OAuth credentials

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/vubon/ExpenseTracker.git
   cd ExpenseTracker
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # For Linux/macOS
   venv\Scripts\activate     # For Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
  You need to export env variables
   ```env
   # Mandatory
   ET_SENDER_EMAIL=your-sender-email@gmail.com
   # Optional
   ET_EMAIL_FIELD_RULES={"Amount": {"type": "amount"}, "Note": {"type": "default"},"Date": {"type": "date", "format": "%d %B %Y at %H:%M:%S"}}
   ET_TARGET_SUBJECT="Payments confirmation,Confirmation of funds transfer,Pay with QR transaction"
   ```

5. Set up Google OAuth credentials:
   - Create credentials in the Google Cloud Console.
   - Download the `credentials.json` file and place it at `.etd` location.

## Usage
1. Start the Expense Tracker:
   ```bash
   python expense_tracker.py
   ```

2. Reports will be displayed periodically, and unread emails will be processed and marked as read.

## How to make a binary file
You can make a binary file for Linux/macOS using the command below. 
After building the binary you can move it inside /usr/local/bin location or your favorite location. 
```bash
pyinstaller --onefile tracker/expense_tracker.py -n etracker
```

## Testing

Run unit tests using `unittest`:
```bash
python -m unittest discover tests
```
With coverage:
```bash
coverage run -m unittest discover tests
```
To view the coverage report:
```bash
coverage report -m
```
Generate HTML report:
```bash
coverage html
```


## Security Notes

- **OAuth Credentials**: Ensure `credentials.json` and `token.pickle` are stored in a secure directory outside the codebase.
- Avoid hard-coding sensitive information in the source code.

## Dependencies

- `google-auth` for Gmail OAuth authentication
- `sqlite3` for database storage
- `tabulate` for displaying data in tabular format

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contribution

Feel free to fork the repository, create issues, or submit pull requests to contribute to the project.

## Acknowledgments

- Google Gmail API documentation
- Python SQLite documentation