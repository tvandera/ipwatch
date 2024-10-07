import unittest
from unittest.mock import mock_open, patch

from ipwatch.ipwatch import Config, InvalidConfigError, DEFAULT_BLACKLIST, DEFAULT_TRY

class TestConfig(unittest.TestCase):

    def setUp(self):
        # This is a valid config file content for testing purposes
        self.valid_config_content = """
        receiver_email = test@example.com
        machine = test-machine
        try_count = 5
        ip_blacklist = 192.168.0.1,192.168.0.2
        dry_run = true
        """

    def test_valid_config(self):
        # Test reading a valid config file
        with patch("builtins.open", mock_open(read_data=self.valid_config_content)):
            config = Config.read("dummy_config.cfg")

        self.assertEqual(config.receiver_email, "test@example.com")
        self.assertEqual(config.machine, "test-machine")
        self.assertEqual(config.try_count, 5)
        self.assertEqual(config.ip_blacklist, "192.168.0.1,192.168.0.2")
        self.assertTrue(config.dry_run)

    def test_missing_required_fields(self):
        # Test config with missing "machine" and "receiver_email"
        invalid_content = """
        try_count = 3
        ip_blacklist = 192.168.0.1
        dry_run = false
        """
        with patch("builtins.open", mock_open(read_data=invalid_content)):
            with self.assertRaises(InvalidConfigError) as cm:
                Config.read("dummy_config.cfg")

            self.assertEqual(cm.exception.missing, "machine")  # Missing machine should trigger an error

        # Test config with missing "receiver_email"
        invalid_content_missing_email = """
        machine = test-machine
        try_count = 3
        """
        with patch("builtins.open", mock_open(read_data=invalid_content_missing_email)):
            with self.assertRaises(InvalidConfigError) as cm:
                Config.read("dummy_config.cfg")
            self.assertEqual(cm.exception.missing, "receiver_email")  # Missing receiver_email should trigger an error

    def test_default_values(self):
        # Test config with missing optional fields, should default
        partial_config_content = """
        receiver_email = test@example.com
        machine = test-machine
        """
        with patch("builtins.open", mock_open(read_data=partial_config_content)):
            config = Config.read("dummy_config.cfg")

        self.assertEqual(config.receiver_email, "test@example.com")
        self.assertEqual(config.machine, "test-machine")
        self.assertEqual(config.try_count, DEFAULT_TRY)  # DEFAULT_TRY
        self.assertEqual(config.ip_blacklist, DEFAULT_BLACKLIST)  # DEFAULT_BLACKLIST
        self.assertFalse(config.dry_run)  # Default False

    def test_file_not_found(self):
        # Test for FileNotFoundError handling
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = FileNotFoundError
            with self.assertRaises(InvalidConfigError) as cm:
                Config.read("non_existing_file.cfg")
            self.assertEqual(cm.exception.fname, "non_existing_file.cfg")

    def test_boolean_casting(self):
        # Test dry_run with different variations of true/false
        config_with_true = """
        receiver_email = test@example.com
        machine = test-machine
        dry_run = TRUE
        """
        config_with_false = """
        receiver_email = test@example.com
        machine = test-machine
        dry_run = false
        """

        with patch("builtins.open", mock_open(read_data=config_with_true)):
            config = Config.read("dummy_config.cfg")
            self.assertTrue(config.dry_run)

        with patch("builtins.open", mock_open(read_data=config_with_false)):
            config = Config.read("dummy_config.cfg")
            self.assertFalse(config.dry_run)


if __name__ == '__main__':
    unittest.main()
