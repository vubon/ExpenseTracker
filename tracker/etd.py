import os
from tracker.logs_config import logger # Added import


class ETDHandler:
    """Manages the application's data directory.

    This class is responsible for ensuring the existence of a dedicated
    directory (`.etd`) in the user's home folder and for providing
    absolute paths to files within this directory. This directory is used
    for storing application-specific data like credentials, tokens, and
    the database.
    """
    def __init__(self):
        """Initializes the ETDHandler.

        Sets the base directory path to `~/.etd` and ensures this
        directory exists by calling `ensure_directory()`.

        Attributes:
            base_dir (str): The absolute path to the application's data
                directory (e.g., '/home/user/.etd').
        """
        self.base_dir = os.path.join(os.path.expanduser("~"), ".etd")
        self.ensure_directory()

    def ensure_directory(self) -> None:
        """Ensures that the base application directory exists.

        If the directory specified by `self.base_dir` does not exist,
        it will be created.

        Raises:
            OSError: If the directory creation fails.
        """
        if not os.path.exists(self.base_dir):
            try:
                os.makedirs(self.base_dir)
                logger.info(f"Application directory created at: {self.base_dir}")
            except OSError as e:
                logger.error(f"Error creating application directory {self.base_dir}: {e}")
                raise # Re-raise the original OSError after logging

    def get_path(self, filename: str) -> str:
        """Constructs the absolute path for a file within the base directory.

        Args:
            filename (str): The name of the file (e.g., 'credentials.json').

        Returns:
            str: The absolute path to the specified file within the
                application's data directory.
        """
        return os.path.join(self.base_dir, filename)
