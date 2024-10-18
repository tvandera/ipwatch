import unittest
from unittest.mock import mock_open, patch

from ipwatch.ipwatch import read_config, make_parser

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
            config = read_config("dummy_config.cfg", make_parser())

        self.assertEqual(config["receiver_email"], "test@example.com")
        self.assertEqual(config["machine"], "test-machine")
        self.assertEqual(config["try_count"], 5)
        self.assertEqual(config["ip_blacklist"], "192.168.0.1,192.168.0.2")
        self.assertTrue(config["dry_run"])

    def test_default_values(self):
        parser = make_parser()

        # Test config with missing optional fields, should default
        partial_config_content = """
        receiver_email = test@example.com
        machine = test-machine
        """
        with patch("builtins.open", mock_open(read_data=partial_config_content)):
            config = read_config("dummy_config.cfg", parser)

        self.assertEqual(config["receiver_email"], "test@example.com")
        self.assertEqual(config["machine"], "test-machine")
        self.assertEqual(config["try_count"], parser.get_default("try_count"))
        self.assertEqual(config["ip_blacklist"], parser.get_default("ip_blacklist"))
        self.assertFalse(config["dry_run"])  # Default False

    def test_file_not_found(self):
        # Test for FileNotFoundError handling
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = FileNotFoundError
            with self.assertRaises(FileNotFoundError) as cm:
                read_config("non_existing_file.cfg", None)


if __name__ == '__main__':
    unittest.main()
