"""
Tests for the InstallationManager
"""
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock, call
from tracker.installer import InstallationManager


class TestInstallationManager(unittest.TestCase):
    """Test cases for InstallationManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.installer = InstallationManager()
    
    @patch('tracker.installer.ETDHandler')
    def test_init(self, mock_etd):
        """Test InstallationManager initialization"""
        mock_etd.return_value.get_path.return_value = '/test/path/oauth_credentials.json'
        installer = InstallationManager()
        
        self.assertIsNotNone(installer.etd_handler)
        self.assertIsNotNone(installer.credentials_path)
    
    @patch('tracker.installer.input', return_value='n')
    @patch('builtins.print')
    def test_confirm_start_declined(self, mock_print, mock_input):
        """Test user declining to start installation"""
        result = self.installer._confirm_start()
        
        self.assertFalse(result)
        mock_input.assert_called_once()
    
    @patch('tracker.installer.input', return_value='Y')
    def test_confirm_start_accepted(self, mock_input):
        """Test user accepting to start installation"""
        result = self.installer._confirm_start()
        
        self.assertTrue(result)
        mock_input.assert_called_once()
    
    @patch('tracker.installer.input', return_value='')
    def test_confirm_start_default(self, mock_input):
        """Test default (empty) response accepts installation"""
        result = self.installer._confirm_start()
        
        self.assertTrue(result)
    
    @patch('tracker.installer.webbrowser.open')
    @patch('tracker.installer.input')
    @patch('builtins.print')
    def test_step_create_project(self, mock_print, mock_input, mock_browser):
        """Test step 1: create Google Cloud project"""
        self.installer._step_create_project()
        
        # Verify browser opened correct URL
        mock_browser.assert_called_once_with(self.installer.URLS['create_project'])
        # Verify user was prompted to continue
        mock_input.assert_called_once()
    
    @patch('tracker.installer.webbrowser.open', side_effect=Exception("Browser error"))
    @patch('tracker.installer.input')
    @patch('builtins.print')
    @patch('tracker.installer.logger')
    def test_step_create_project_browser_failure(self, mock_logger, mock_print, mock_input, mock_browser):
        """Test step 1 handles browser opening failure"""
        self.installer._step_create_project()
        
        # Should log warning and continue
        mock_logger.warning.assert_called_once()
        mock_input.assert_called_once()
    
    @patch('tracker.installer.input', side_effect=['', '', 'valid-client-id'])
    @patch('builtins.print')
    def test_step_create_credentials_retry_client_id(self, mock_print, mock_input):
        """Test step 3 retries when CLIENT_ID is empty"""
        with patch('tracker.installer.webbrowser.open'):
            with patch('tracker.installer.input', side_effect=['', '', 'client-id', 'client-secret']):
                client_id, client_secret = self.installer._step_create_credentials()
        
        self.assertEqual(client_id, 'client-id')
        self.assertEqual(client_secret, 'client-secret')
    
    @patch('os.makedirs')
    @patch('builtins.open', create=True)
    @patch('os.chmod')
    @patch('builtins.print')
    def test_save_credentials_success(self, mock_print, mock_chmod, mock_open, mock_makedirs):
        """Test saving credentials successfully"""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        result = self.installer._save_credentials('test-client-id', 'test-secret')
        
        self.assertTrue(result)
        mock_makedirs.assert_called_once()
        mock_chmod.assert_called_once_with(self.installer.credentials_path, 0o600)
    
    @patch('os.makedirs', side_effect=OSError("Permission denied"))
    @patch('builtins.print')
    @patch('tracker.installer.logger')
    def test_save_credentials_failure(self, mock_logger, mock_print, mock_makedirs):
        """Test handling credentials save failure"""
        result = self.installer._save_credentials('test-client-id', 'test-secret')
        
        self.assertFalse(result)
        mock_logger.error.assert_called_once()
    
    @patch('os.path.exists', return_value=True)
    @patch('tracker.gmail_authenticator.GmailAuthenticator')
    def test_is_installed_true(self, mock_auth, mock_exists):
        """Test is_installed returns True when both files exist"""
        result = self.installer.is_installed()
        
        self.assertTrue(result)
    
    @patch('os.path.exists', return_value=False)
    @patch('tracker.gmail_authenticator.GmailAuthenticator')
    def test_is_installed_false(self, mock_auth, mock_exists):
        """Test is_installed returns False when files don't exist"""
        result = self.installer.is_installed()
        
        self.assertFalse(result)
    
    @patch.object(InstallationManager, '_print_welcome')
    @patch.object(InstallationManager, '_confirm_start', return_value=False)
    @patch('builtins.print')
    def test_run_cancelled(self, mock_print, mock_confirm, mock_welcome):
        """Test run exits early when user cancels"""
        result = self.installer.run()
        
        self.assertFalse(result)
        mock_welcome.assert_called_once()
        mock_confirm.assert_called_once()
    
    @patch.object(InstallationManager, '_print_welcome')
    @patch.object(InstallationManager, '_confirm_start', return_value=True)
    @patch.object(InstallationManager, '_step_create_project')
    @patch.object(InstallationManager, '_step_enable_gmail_api')
    @patch.object(InstallationManager, '_step_create_credentials', return_value=('client-id', 'secret'))
    @patch.object(InstallationManager, '_save_credentials', return_value=True)
    @patch.object(InstallationManager, '_step_authenticate', return_value=True)
    @patch.object(InstallationManager, '_print_success')
    def test_run_complete_flow(self, mock_success, mock_auth, mock_save, mock_creds, 
                               mock_gmail, mock_project, mock_confirm, mock_welcome):
        """Test complete installation flow succeeds"""
        result = self.installer.run()
        
        self.assertTrue(result)
        mock_welcome.assert_called_once()
        mock_confirm.assert_called_once()
        mock_project.assert_called_once()
        mock_gmail.assert_called_once()
        mock_creds.assert_called_once()
        mock_save.assert_called_once_with('client-id', 'secret')
        mock_auth.assert_called_once()
        mock_success.assert_called_once()


if __name__ == '__main__':
    unittest.main()
