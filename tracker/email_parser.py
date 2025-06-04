import base64
import json
import os
import re
from datetime import datetime
from dateutil.parser import parse

from bs4 import BeautifulSoup

from tracker.logs_config import logger


class EmailParser:
    """
    A class responsible for fetching, parsing, and extracting data from emails.
    Attributes:
        message (str): The decoded email body.
        default_rules (dict): A dictionary of default processing rules for common fields.
        custom_rules (dict): A dictionary of custom processing rules loaded from environment variables.
    Methods:
        __init__(message): Initializes the EmailParser with the provided email message.
        _define_default_rules(): Defines default processing rules for common fields (amount, date, note).
        _load_rules_from_env(): Loads custom processing rules from the environment variable `ET_EMAIL_FIELD_RULES`.
        process_amount(value): Processes an amount value by removing non-numeric characters and converting it to a float.
        process_date(value, date_format): Processes a date value by parsing it with the provided date format.
        process_default(value): Processes a field using default logic (e.g., trimming and converting to lowercase).
        determine_rule(field_name): Determines the processing rule for a given field name based on custom or default rules.
        process_field(field_name, raw_value): Processes a field by applying the appropriate processing rule.
        get_field_names(): Returns a set of all the field names (keys) from both default and custom rules.
        decode_email_body(message): Decodes the email body from Base64 format, handling multipart and single-part emails.
        extract_tags_values_from_body(): Extracts key values (amount, note, etc.) from the email body using
        BeautifulSoup and regex.
    """

    def __init__(self, message: dict):
        """Initializes the EmailParser with the provided email message.

        Args:
            message (dict): The raw email message to be processed.

        Attributes:
            message (str): The decoded body of the email.
            default_rules (dict): Default processing rules for common field types.
            field_types (dict): Field type processing rules for custom rules field.
            custom_rules (dict): Custom processing rules loaded from the environment
                variable `ET_EMAIL_FIELD_RULES`.
        """
        self.message = self.decode_email_body(message)
        self.default_rules = self._define_default_rules()
        self.field_types = self._define_field_types()
        self.custom_rules = self._load_rules_from_env()

    def _define_default_rules(self) -> dict:
        """Defines default rules for common processing types.

        Returns:
            dict: A dictionary of default processing functions mapped to field types
                (e.g., "amount", "date", "note").
        """
        return {
            "amount": self.process_amount,
            "date": self.process_date,
            "note": self.process_note
        }

    def _define_field_types(self) -> dict:
        """Defines field types and their corresponding processing functions.

        Returns:
            dict: A dictionary mapping field type names to their processing methods.
        """
        return {
            "amount": self.process_amount,
            "date": self.process_date,
            "default": self.process_default,
            "note": self.process_note
        }

    @staticmethod
    def _load_rules_from_env() -> dict:
        """Loads custom rules from the `ET_EMAIL_FIELD_RULES` environment variable.

        The environment variable should contain a JSON string defining custom rules
        for processing email fields. For example:

        ```json
        {
            "Amount": {"type": "amount"},
            "Note": {"type": "default"},
            "Date": {"type": "date", "format": "%d %B %Y at %H:%M:%S"}
        }
        ```

        Returns:
            dict: A dictionary containing custom field processing rules. Returns an
                empty dictionary if the environment variable is not set or contains
                invalid JSON.
        """
        raw_rules = os.getenv("ET_EMAIL_FIELD_RULES", '{}')
        try:
            return json.loads(raw_rules)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in ET_EMAIL_FIELD_RULES: {e}")
            return {}

    @staticmethod
    def process_amount(value: str) -> float | None:
        """Processes an amount field by extracting and converting it to a float.

        Uses regex to find a numeric value (allowing for commas and decimals)
        preceded by "Amount".

        Args:
            value (str): The raw string value potentially containing the amount.

        Returns:
            float | None: The extracted amount as a float, or None if no amount
                is found or if conversion fails.
        """
        matched_value = re.search(r"Amount.*?([\d,.]+)", value)
        return float(matched_value.group(1).replace(",", "")) if matched_value else None

    def process_date(self, value: str) -> datetime | None:
        """Processes a date field using dateutil.parser.parse.

        Attempts to extract a date/time string from common textual contexts
        (e.g., "Date: March 2, 2025 21:15:27") before passing to `parse`.
        If parsing is successful, returns the datetime object.
        If parsing fails, logs an error and returns None.

        Args:
            value (str): The raw string value potentially containing the date.

        Returns:
            datetime | None: The parsed datetime object, or None if parsing fails.
        """
        # Regex to find common date patterns, trying to isolate the date string
        # This regex attempts to capture a date/time string that might be prefixed with "Date: "
        # and might be followed by " at " and more time details, or a timezone.
        # It's a general attempt and might need refinement based on actual email formats.
        date_pattern = r"(?:Date:?\s*)?([\w\s,:\./-]+?)(?:\s*at\s*[\w\s,:\./-]+)?(?:[A-Z]{3,}|[+-]\d{2}:\d{2})?$"
        match = re.search(date_pattern, value, re.IGNORECASE)

        date_to_parse = value # Default to the original value
        if match:
            # If a pattern is matched, try to use the first captured group,
            # which should be the cleaner date/time string.
            # This is a simple heuristic; more complex emails might need more robust extraction.
            # Example: "Date March 2, 2025 at 21:15:27" -> group(1) might be "March 2, 2025"
            # Example: "Date: 2025-03-02 21:15:27" -> group(1) might be "2025-03-02 21:15:27"
            # The regex tries to capture the core date/time part.
             # Let's try a few common explicit patterns first
            explicit_patterns = [
                r"Date:?\s*(\w+\s+\d{1,2},\s+\d{4}\s+\d{2}:\d{2}:\d{2})",  # "Date: March 2, 2025 21:15:27"
                r"Date:?\s*(\d{1,2}\s+\w+\s+\d{4}\s+at\s+\d{2}:\d{2}:\d{2})", # "Date: 2 March 2025 at 21:15:27"
                r"Date:?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})" # "Date: 2025-03-02 21:15:27"
            ]
            extracted_date_str = None
            for pattern in explicit_patterns:
                search_match = re.search(pattern, value, re.IGNORECASE)
                if search_match and search_match.group(1):
                    extracted_date_str = search_match.group(1).strip()
                    break

            if extracted_date_str:
                date_to_parse = extracted_date_str
            else: # Fallback to a more general extraction if specific patterns don't match
                general_match = re.search(r"Date:?\s*(.*)", value, re.IGNORECASE)
                if general_match and general_match.group(1):
                    # Further clean up common irrelevant parts if possible
                    # This is very heuristic and might need adjustments
                    date_to_parse = general_match.group(1).strip()
                    # Remove common timezone/day parts that dateutil might handle or get confused by
                    date_to_parse = re.sub(r"\s+[A-Z]{3,}\s*$", "", date_to_parse) # Remove trailing timezone like EST
                    date_to_parse = re.sub(r"\s+\([A-Za-z\s]+\)\s*$", "", date_to_parse) # Remove day in parenthesis (e.g. (Monday))

        if not date_to_parse.strip():
            logger.warning(f"Date string is empty after extraction attempts from: {value}")
            return None

        try:
            logger.info(f"Attempting to parse date string: '{date_to_parse}' from original value: '{value}'")
            return parse(date_to_parse)
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing date string '{date_to_parse}' (from original: '{value}'): {e}")
            return None

    @staticmethod
    def process_default(value: str) -> str:
        """Processes a generic field with default logic.

        The default logic involves stripping leading/trailing whitespace and
        converting the string to lowercase. If the value is empty or None
        after stripping, it returns "unknown".

        Args:
            value (str): The raw string value to be processed.

        Returns:
            str: The processed string value, or "unknown" if the input is empty.
        """
        processed_value = value.strip().lower() if value else ""
        return processed_value if processed_value else "unknown"

    @staticmethod
    def process_note(value: str) -> str:
        """Processes a note field by extracting the content following "Note".

        Uses regex to find the content immediately following "Note " (case-insensitive)
        and converts it to lowercase.

        Args:
            value (str): The raw string value potentially containing the note.

        Returns:
            str: The extracted note content in lowercase, or "unknown" if no note
                is found or if the content is empty.
        """
        matched_value = re.search(r"Note\s+(\w+)", value, re.IGNORECASE)
        return matched_value.group(1).lower() if matched_value else "unknown"

    def determine_rule(self, field_name: str):
        """Determines the processing rule for a given field name.

        It first checks for a custom rule defined for the `field_name`. If found,
        it retrieves the processing type (e.g., "date", "amount") and any
        associated parameters (e.g., "format" for dates). It then returns the
        corresponding processing method.

        If no custom rule is found, it attempts to find a default rule by
        matching the lowercase `field_name` (e.g., "date" maps to `process_date`).

        Args:
            field_name (str): The name of the field to determine the rule for.

        Returns:
            function: The processing function (method) to be used for the field.

        Raises:
            ValueError: If a custom rule specifies an invalid `type`, if a "date"
                type rule is missing a `format`, or if no processing rule
                (custom or default) can be found for the `field_name`.
        """
        # Check user-based rule at first if exist for that field
        if field_name in self.custom_rules:
            custom_rule = self.custom_rules[field_name]
            field_type = custom_rule.get("type", "").lower()

            if field_type in self.field_types:
                if field_type == "date":
                    # Date format is no longer needed for process_date
                    return lambda value: self.process_date(value)
                return self.field_types[field_type]

            # Ensure the error message for invalid field type is clear
            raise ValueError(f"Invalid field type '{field_type}' defined in custom rules for field: {field_name}. Supported types are: {list(self.field_types.keys())}")

        # Use default rules based on inferred field name
        if field_name.lower() in self.default_rules:
            return self.default_rules[field_name.lower()]

        # If no rule found, raise an exception or return None
        raise ValueError(f"No processing rule found for field: {field_name}")

    def process_field(self, field_name: str, raw_value: str):
        """Processes a field by applying the dynamically determined processing rule.

        This method uses `determine_rule` to get the appropriate function for
        the `field_name` and then calls that function with `raw_value`.

        Args:
            field_name (str): The name of the field to process (e.g., "Amount", "Date").
            raw_value (str): The raw string value extracted from the email that
                corresponds to this field.

        Returns:
            The processed value. The type of this value depends on the processing
            rule applied (e.g., float for "amount", datetime for "date", string
            for "note" or "default"). Can also be None if processing fails.

        Raises:
            ValueError: If `determine_rule` cannot find a rule for `field_name`.
        """
        processing_rule = self.determine_rule(field_name)
        return processing_rule(raw_value)

    def get_field_names(self) -> set[str]:
        """Combines field names from default and custom rules into a single set.

        It applies a case transformation (title, lower, or upper) to the default
        rule keys based on the predominant case style detected in custom rule keys
        by `_determine_case_function_from_custom_rules`.

        Returns:
            set[str]: A set containing all unique field names from both default
                and custom rules, with consistent casing.

        Raises:
            ValueError: If `_determine_case_function_from_custom_rules` cannot
                determine a uniform case for custom rule keys.
        """
        case_func = self._determine_case_function_from_custom_rules()
        return {case_func(key) for key in self.default_rules.keys()}.union(self.custom_rules.keys())

    def _determine_case_function_from_custom_rules(self) -> callable:
        """Determines the appropriate string case function from custom rule keys.

        Inspects the keys of `self.custom_rules` to see if they are all in
        title case, lowercase, or uppercase.

        Returns:
            callable: The corresponding string method (str.title, str.lower,
                or str.upper).

        Raises:
            ValueError: If the custom rule keys do not follow a consistent
                casing (all title, all lower, or all upper).
        """
        # Check the case format of all custom_rules keys
        all_keys = self.custom_rules.keys()

        if all(key.istitle() for key in all_keys):
            return str.title
        elif all(key.islower() for key in all_keys):
            return str.lower
        elif all(key.isupper() for key in all_keys):
            return str.upper
        else:
            raise ValueError("Custom rules keys must be uniformly in title, lower, or upper case.")

    @staticmethod
    def decode_email_body(message: dict) -> str | None:
        """Decodes the email body from a raw email message dictionary.

        Handles both single-part and multipart emails. For multipart emails,
        it specifically looks for the 'text/plain' part. The body is expected
        to be Base64 URL-safe encoded.

        Args:
            message (dict): The raw email message object, typically from an API
                like Gmail API, containing payload and body information.

        Returns:
            str | None: The decoded email body as a UTF-8 string, or None if
                the body cannot be found or decoded.
        """
        payload = message.get('payload', {})

        if 'parts' in payload and payload['parts']:  # Multipart email
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':  # Look for plain text part
                    body = part.get('body', {}).get('data', '')
                    return base64.urlsafe_b64decode(body).decode('utf-8')
        else:  # Single-part email
            body = payload.get('body', {}).get('data', '')
            if body:
                return base64.urlsafe_b64decode(body).decode('utf-8')
        return None

    def extract_tags_values_from_body(self) -> dict:
        """Extracts field-value pairs from the decoded email body.

        It first parses the HTML email body using BeautifulSoup to get the raw text.
        Then, for each field name obtained from `get_field_names`, it attempts
        to process the raw text to extract and transform the corresponding value
        using `process_field`.

        Returns:
            dict: A dictionary where keys are field names (e.g., "Amount", "Date")
                and values are their processed counterparts. If processing for a
                field fails (e.g., due to a ValueError from `process_field` or
                `determine_rule`), the value for that field will be None.
        """
        soup = BeautifulSoup(self.message, 'html.parser')
        raw_text = " ".join(soup.get_text().split()).strip()

        extract_data = {}

        for field in self.get_field_names():
            try:
                extract_data[field] = self.process_field(field_name=field, raw_value=raw_text)
            except ValueError as err:
                logger.info(f"Data processor error: {err}")
                extract_data[field] = None

        return extract_data
