from typing import Any, List, Optional

from tracker.logs_config import logger


class EmailFetcher:
    """
    Handles fetching emails from Gmail.
    """

    def __init__(self, service):
        """
        Initialize the EmailFetcher with a Gmail API service.
        Args:
            service: Authenticated Gmail API service object.
        """
        self.service = service

    def list_unread_messages(self, sender: str) -> List[dict]:
        """
        Fetch unread messages matching the sender and subject filter.
        """
        results = self.service.users().messages().list(
            userId='me',
            q=f"from:{sender} is:unread"
        ).execute()
        return results.get('messages', [])

    def filter_unread_messages(self, sender: str, target_subjects: List[str]) -> List[dict]:
        unread_messages = self.list_unread_messages(sender=sender)
        unread_messages_list = []
        if not unread_messages:
            logger.info("No more emails")
            return unread_messages_list

        for msg in unread_messages:
            message = self.get_message_details(msg.get("id"))
            if not message:
                continue

            if self.is_target_subject(target_subjects=target_subjects, message=message):
                unread_messages_list.append(message)

        return unread_messages_list

    def get_message_details(self, message_id: str) -> Any | None:
        """
        Fetch detailed email data for a given message ID.
        """
        try:
            return self.service.users().messages().get(userId='me', id=message_id).execute()
        except Exception as e:
            logger.error(f"Failed to fetch details for message ID {message_id}: {e}")
            return None

    def mark_message_as_read(self, message_id: str | None) -> Optional[None]:
        """
        Mark the email as read after processing.
        """
        if not message_id:
            return

        self.service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()

    @staticmethod
    def get_email_subject(message) -> Any | None:
        """
        Extract the email subject from the message headers.
        """
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'] == 'Subject':
                return header['value']
        return None

    def is_target_subject(self, target_subjects: List[str], message) -> bool:
        """
        Check if the email subject matches any of the target subjects.
        Args:
            target_subjects (list): List of subjects to match.
            message (dict): The email message to check.
        Returns:
            bool: True if the email subject matches any target subject, False otherwise.
        """
        email_subject = self.get_email_subject(message)
        if not email_subject:
            return False

        if any(subject.lower() in email_subject.lower() for subject in target_subjects):
            return True

        return False
