import base64
import json
import os
import re
import binascii
from datetime import datetime

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

    def __init__(self, message):
        """
        Initializes the EmailParser with the provided email message.
        Args:
            message (dict): The raw email message to be processed.
        Sets up:
            - `self.message`: The decoded body of the email.
            - `self.default_rules`: Default processing rules for common field types.
            - `self.field_types`: Field type processing rules for custom rules field.
            - `self.custom_rules`: Custom processing rules loaded from the environment variable `ET_EMAIL_FIELD_RULES`.
        """
        self.message = self.decode_email_body(message)
        self.default_rules = self._define_default_rules()
        self.field_types = self._define_field_types()
        self.custom_rules = self._load_rules_from_env()

    def _define_default_rules(self) -> dict:
        """
        Defines default rules for common processing types such as "amount", "date", and "note".
        Returns:
            dict: A dictionary of default processing functions mapped to field types.
        """
        return {
            "amount": self.process_amount,
            "date": self.process_date,
            "note": self.process_note
        }

    def _define_field_types(self) -> dict:
        """
            Define field types and their corresponding processing functions.
        """
        return {
            "amount": self.process_amount,
            "date": self.process_date,
            "default": self.process_default,
            "note": self.process_note
        }

    @staticmethod
    def _load_rules_from_env() -> dict:
        """
        Loads custom rules for processing fields from the environment variable `ET_EMAIL_FIELD_RULES`.
        Example:
            Export the environment variable `ET_EMAIL_FIELD_RULES` as a JSON string:
            export ET_EMAIL_FIELD_RULES='{
                "Amount": {"type": "amount"},
                "Note": {"type": "default"},
                "Date": {"type": "date", "format": "%d %B %Y at %H:%M:%S"}
            }'
        Returns:
            dict: A dictionary containing custom field processing rules.
        """
        raw_rules = os.getenv("ET_EMAIL_FIELD_RULES", '{}')
        try:
            return json.loads(raw_rules)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in ET_EMAIL_FIELD_RULES: {e}")
            return {}

    @staticmethod
    def process_amount(value: str) -> float | None:
        """
        Processes an amount field by removing non-numeric characters and converting it to a float.
        Args:
            value (str): The raw amount value to be processed.
        Returns:
            float | None: The processed amount as a float, or None if the value cannot be parsed.
        """
        matched_value = re.search(r"(?i)\bamount\b[^\d-]*([-+]?\d[\d,]*(?:\.\d+)?)", value)
        if not matched_value:
            matched_value = re.search(r"([-+]?\d[\d,]*(?:\.\d+)?)", value)

        return float(matched_value.group(1).replace(",", "")) if matched_value else None

    def process_date(self, value: str, date_format: str = "%d %B %Y at %H:%M:%S") -> datetime:
        """
        Processes a date field by parsing it with the provided format.
        Args:
            value (str): The raw date value to be processed.
            date_format (str, optional): The format to parse the date.Defaults to "%d %B %Y at %H:%M:%S".
        Returns:
            datetime: The parsed date as a `datetime` object.
        Raises:
            ValueError: If the date value does not match the specified format.
        """
        normalized_input = re.sub(r"(?i)\bdate\b\s*:?", "", value).strip()

        if date_format:
            try:
                return datetime.strptime(normalized_input, date_format)
            except ValueError:
                pass

        date_str, inferred_format = self.clean_and_normalize_date(value)
        if not date_str or not inferred_format:
            raise ValueError(f"Error parsing date value: '{value}'")

        try:
            return datetime.strptime(date_str, inferred_format)
        except ValueError as err:
            raise ValueError(f"Error parsing date with format {inferred_format}: {err}")

    @staticmethod
    def clean_and_normalize_date(value: str) -> tuple[str, str] | tuple[None, None]:
        """
        Cleans and normalizes the raw date string by handling inconsistent spacing and patterns.

        :param value: The raw date string to clean.
        :return: A cleaned and normalized date string.
        """
        patterns_formats = [
            (r"(?:Date )?(\d{1,2}) ([\w]+) (\d{4}) at (\d{2}:\d{2}:\d{2})", "%d %B %Y %H:%M:%S"), #"2 March 2025 at 21:15:27"
            (r"(?:Date )?([\w]+) (\d{1,2}), (\d{4}) (\d{2}:\d{2}:\d{2})", "%B %d, %Y %H:%M:%S"), #"March 2, 2025 21:15:27"
            (r"(?:Date )?(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2}:\d{2})", "%Y-%m-%d %H:%M:%S"), #"2025-03-02 21:15:27"
            (r"(?:Date )?(\d{1,2})/(\d{1,2})/(\d{4}) (\d{2}:\d{2}:\d{2})", "%d/%m/%Y %H:%M:%S"), #"02/03/2025 21:15:27"
            (r"(?:Date )?(\d{1,2}) ([\w]{3}) (\d{4}) at (\d{2}:\d{2}:\d{2})", "%d %b %Y %H:%M:%S") #"2 Mar 2025 at 21:15:27"
        ]

        for pattern, format_str in patterns_formats:
            match = re.search(pattern, value)
            if match:
                if format_str == "%B %d, %Y %H:%M:%S":  # "March 2, 2025 21:15:27"
                    date_str = f"{match.group(1)} {match.group(2)}, {match.group(3)} {match.group(4)}"
                elif format_str == "%Y-%m-%d %H:%M:%S":  # "2025-03-02 21:15:27"
                    date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)} {match.group(4)}"
                elif format_str == "%d/%m/%Y %H:%M:%S":  # "02/03/2025 21:15:27"
                    date_str = f"{match.group(1)}/{match.group(2)}/{match.group(3)} {match.group(4)}"
                else:
                    date_str = " ".join(match.groups())  # Other formats can be directly joined

                return date_str, format_str

        return None, None

    @staticmethod
    def process_default(value: str) -> str:
        """
        Processes a field using default logic (trimming and converting to lowercase).
        Args:
            value (str): The raw value to be processed.
        Returns:
            str: The processed value, or "unknown" if the value is empty.
        """
        return value.strip().lower() if value else "unknown"

    @staticmethod
    def process_note(value: str) -> str:
        """
          Processes a field using default logic (trimming and converting to lowercase).
        Args:
            value (str): The raw value to be processed.
        Returns:
            str: The processed value, or "unknown" if the value is empty.
        """
        matched_value = re.search(r"Note\s+(\w+)", value, re.IGNORECASE)
        return matched_value.group(1).lower() if matched_value else "unknown"

    def determine_rule(self, field_name: str):
        """
        Determines the processing rule for a given field name based on custom or default rules.
        Args:
            field_name (str): The name of the field to process.
        Returns:
            function: The processing function for the field.
        Raises:
            ValueError: If no processing rule is found for the field.
        """

        # Check user-based rule at first if exist for that field
        if field_name in self.custom_rules:
            custom_rule = self.custom_rules[field_name]
            field_type = custom_rule.get("type", "").lower()

            if field_type in self.field_types:
                if field_type == "date":
                    date_format = custom_rule.get("format")
                    if not date_format:
                        raise ValueError("Date format must be provided for date processing")
                    return lambda value: self.process_date(value, date_format)

                return self.field_types[field_type]

            raise ValueError(f"Invalid field type '{field_type}' for field: {field_name}")

        # Use default rules based on inferred field name
        if field_name.lower() in self.default_rules:
            return self.default_rules[field_name.lower()]

        # If no rule found, raise an exception or return None
        raise ValueError(f"No processing rule found for field: {field_name}")

    def process_field(self, field_name, raw_value):
        """
        Processes a field by applying the appropriate processing rule.
        Args:
            field_name (str): The name of the field to process.
            raw_value (str): The raw value to be processed.
        Returns:
            The processed value, which can be of type `float`, `datetime`, `str`, or `None`.
        """
        processing_rule = self.determine_rule(field_name)
        return processing_rule(raw_value)

    def get_field_names(self):
        """
        Combine key names from both default and custom rules.
        Returns:
            set: A unified set of key names from both rules.
        """
        case_func = self._determine_case_function_from_custom_rules()
        return {case_func(key) for key in self.default_rules.keys()}.union(self.custom_rules.keys())

    def _determine_case_function_from_custom_rules(self):
        """
        Determine the case function (title, lower, or upper) based on the keys in custom_rules.
        Returns:
            function: The case function to apply (either title(), lower(), or upper()).
        """
        # Check the case format of all custom_rules keys
        all_keys = self.custom_rules.keys()

        if not all_keys:
            return str.title

        if all(key.istitle() for key in all_keys):
            return str.title
        elif all(key.islower() for key in all_keys):
            return str.lower
        elif all(key.isupper() for key in all_keys):
            return str.upper
        else:
            return lambda key: key

    @staticmethod
    def decode_email_body(message):
        """
        Decodes the email body from Base64 format, handling both multipart and single-part emails.
        Args:
            message (dict): The email message to decode.
        Returns:
            str: The decoded email body as a string.
        """
        payload = message.get('payload', {})

        if 'parts' in payload and payload['parts']:  # Multipart email
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':  # Look for plain text part
                    body = part.get('body', {}).get('data', '')
                    try:
                        return base64.urlsafe_b64decode(body).decode('utf-8')
                    except (ValueError, binascii.Error, UnicodeDecodeError) as err:
                        logger.error(f"Failed to decode multipart email body: {err}")
                        return ""
        else:  # Single-part email
            body = payload.get('body', {}).get('data', '')
            if body:
                try:
                    return base64.urlsafe_b64decode(body).decode('utf-8')
                except (ValueError, binascii.Error, UnicodeDecodeError) as err:
                    logger.error(f"Failed to decode email body: {err}")
                    return ""

        return ""

    def extract_tags_values_from_body(self):
        """
        Extracts key-value pairs (such as "Amount" and "Note") from the email body using BeautifulSoup and regex.
        Returns:
            dict: A dictionary of field names (e.g., "Amount", "Date") mapped to their processed values.
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
