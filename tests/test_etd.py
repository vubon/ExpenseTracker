import unittest
from unittest.mock import patch
import os

from tracker.etd import ETDHandler


class TestETDHandler(unittest.TestCase):
    @patch('os.chmod')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('os.path.expanduser')
    def test_init_directory_creation(self, mock_expanduser, mock_makedirs, mock_exists, mock_chmod):
        # Setup mock behavior
        mock_expanduser.return_value = '/mock/home'
        mock_exists.return_value = False

        # Initialize ETDHandler
        ETDHandler()

        # Assert if the directory path was correctly created
        mock_expanduser.assert_called_with("~")
        mock_exists.assert_called_with('/mock/home/.etd')
        mock_makedirs.assert_called_with('/mock/home/.etd', mode=0o700, exist_ok=True)
        mock_chmod.assert_called_with('/mock/home/.etd', 0o700)

    @patch('os.chmod')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('os.path.expanduser')
    def test_init_directory_already_exists(self, mock_expanduser, mock_makedirs, mock_exists, mock_chmod):
        # Setup mock behavior for existing directory
        mock_expanduser.return_value = '/mock/home'
        mock_exists.return_value = True

        # Initialize ETDHandler
        ETDHandler()

        # Assert makedirs was not called if directory already exists
        mock_exists.assert_called_with('/mock/home/.etd')
        mock_makedirs.assert_not_called()
        mock_chmod.assert_called_with('/mock/home/.etd', 0o700)

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('os.path.expanduser')
    @patch('os.chmod', side_effect=OSError("permission denied"))
    def test_init_directory_chmod_error(self, mock_chmod, mock_expanduser, mock_makedirs, mock_exists):
        mock_expanduser.return_value = '/mock/home'
        mock_exists.return_value = True

        ETDHandler()

        mock_makedirs.assert_not_called()
        mock_chmod.assert_called_with('/mock/home/.etd', 0o700)

    def test_get_path(self):
        # Initialize ETDHandler
        handler = ETDHandler()

        # Test get_path
        result = handler.get_path("example.txt")
        expected_result = os.path.join(handler.base_dir, "example.txt")

        # Assert that the path returned is correct
        self.assertEqual(result, expected_result)
