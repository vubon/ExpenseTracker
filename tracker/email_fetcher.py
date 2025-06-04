from typing import Any, List, Optional

from tracker.logs_config import logger


class EmailFetcher:
    """Handles fetching and processing emails from a Gmail account.

    This class uses an authenticated Gmail API service to list, filter,
    and manage email messages.
    """

    def __init__(self, service: Any):
        """Initializes the EmailFetcher.

        Args:
            service (Any): An authenticated Gmail API service object, typically
                obtained from `GmailAuthenticator.authenticate()`.
        """
        self.service = service

    def list_unread_messages(self, sender: str) -> List[dict]:
        """Lists unread messages from a specific sender.

        Args:
            sender (str): The email address of the sender to filter messages from.

        Returns:
            List[dict]: A list of message resource dictionaries for unread emails
                from the specified sender. Returns an empty list if no such
                messages are found or an error occurs.
        """
        results = self.service.users().messages().list(
            userId='me',
            q=f"from:{sender} is:unread"
        ).execute()
        return results.get('messages', [])

    def filter_unread_messages(self, sender: str, target_subjects: List[str]) -> List[dict]:
        """Filters unread messages by sender and a list of target subjects.

        It first lists unread messages from the sender, then retrieves details
        for each message and checks if its subject contains any of the target subjects.

        Args:
            sender (str): The email address of the sender.
            target_subjects (List[str]): A list of subject strings to look for.
                The check is case-insensitive.

        Returns:
            List[dict]: A list of detailed message objects (dictionaries) that
                match the criteria. Returns an empty list if no matching emails
                are found.
        """
        unread_messages = self.list_unread_messages(sender=sender)
        unread_messages_list = []
        if not unread_messages:
            logger.info("No more emails")
            return unread_messages_list

        for msg_summary in unread_messages: # msg_summary is a dict like {'id': '...', 'threadId': '...'}
            message_id = msg_summary.get("id")
            if not message_id:
                logger.warning(f"Found a message summary without an ID: {msg_summary}")
                continue

            message_details = self.get_message_details(message_id)
            if not message_details:
                continue

            if self.is_target_subject(target_subjects=target_subjects, message=message_details):
                unread_messages_list.append(message_details)

        return unread_messages_list

    def get_message_details(self, message_id: str) -> Optional[dict]:
        """Retrieves the full details of a specific email message.

        Args:
            message_id (str): The unique ID of the email message.

        Returns:
            Optional[dict]: A dictionary containing the full message resource
                (including payload, headers, etc.), or None if an error occurs
                during fetching (e.g., message not found, API error).
        """
        try:
            return self.service.users().messages().get(userId='me', id=message_id).execute()
        except Exception as e:
            logger.error(f"Failed to fetch details for message ID {message_id}: {e}")
            return None

    def mark_message_as_read(self, message_id: Optional[str]) -> None:
        """Marks a specific email message as read (by removing the 'UNREAD' label).

        If `message_id` is None, the method does nothing.

        Args:
            message_id (Optional[str]): The unique ID of the email message to mark as read.

        Returns:
            None
        """
        if not message_id:
            logger.warning("Attempted to mark message as read with no message_id.")
            return

        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"Message ID {message_id} marked as read.")
        except Exception as e:
            logger.error(f"Failed to mark message ID {message_id} as read: {e}")

    @staticmethod
    def get_email_subject(message: dict) -> Optional[str]:
        """Extracts the subject of an email message from its headers.

        Args:
            message (dict): A dictionary representing an email message resource,
                expected to have a 'payload' key with 'headers'.

        Returns:
            Optional[str]: The subject string if found, otherwise None.
        """
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'] == 'Subject':
                return header['value']
        return None

    def is_target_subject(self, target_subjects: List[str], message: dict) -> bool:
        """Checks if the email's subject matches any of the target subjects.

        The comparison is case-insensitive.

        Args:
            target_subjects (List[str]): A list of subject strings to check against.
            message (dict): The email message object (dictionary) containing headers.

        Returns:
            bool: True if the email's subject contains any of the target subjects,
                  False otherwise (including if the email has no subject).
        """
        email_subject = self.get_email_subject(message)
        if not email_subject:
            return False

        if any(subject.lower() in email_subject.lower() for subject in target_subjects):
            return True

        return False
