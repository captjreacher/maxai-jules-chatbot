# chatbot/tests/test_chatbot_logic.py
import unittest
import csv
import os
import sys
from unittest.mock import patch

# Adjust sys.path to include the parent directory (chatbot project root)
# This allows finding the 'chatbot.core' and 'chatbot.integrations' modules
# __file__ is /app/chatbot/tests/test_chatbot_logic.py
# os.path.dirname(__file__) is /app/chatbot/tests
# PROJECT_ROOT should be /app/chatbot
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now, attempt to import the modules
try:
    from chatbot.core.rules_based_chatbot import load_rules_from_csv, get_response
    # We also need to potentially reload rules in get_response or manipulate its 'rules' global
    # For simplicity in this test, we might re-assign the global 'rules' dictionary
    # or ensure load_rules_from_csv is called by get_response implicitly.
    # The current rules_based_chatbot loads rules globally at import time.
    # To test get_response with specific rules, we need to control this.
    import chatbot.core.rules_based_chatbot as core_chatbot
except ImportError as e:
    print(f"Error importing chatbot modules: {e}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"sys.path: {sys.path}")
    # Define dummy functions if import fails, so the rest of the test file can be parsed
    def load_rules_from_csv(file_path): return {}
    def get_response(user_input): return "IMPORT_ERROR"
    class core_chatbot: rules = {}


# Define the path to the data directory consistently
DATA_DIR = os.path.join(PROJECT_ROOT, "chatbot", "data")
ORIGINAL_RULES_CSV_PATH = os.path.join(DATA_DIR, "rules.csv")
TEST_RULES_CSV_PATH = os.path.join(DATA_DIR, "test_rules.csv") # Used by some tests directly

class TestChatbotLogic(unittest.TestCase):

    def setUp(self):
        """Setup method to prepare for each test."""
        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)

        # Backup original rules.csv if it exists
        self.original_rules_existed = os.path.exists(ORIGINAL_RULES_CSV_PATH)
        if self.original_rules_existed:
            self.backup_rules_csv_path = os.path.join(DATA_DIR, "rules.csv.backup")
            os.rename(ORIGINAL_RULES_CSV_PATH, self.backup_rules_csv_path)

    def tearDown(self):
        """Teardown method to clean up after each test."""
        # Delete any test-specific rules.csv
        if os.path.exists(ORIGINAL_RULES_CSV_PATH):
            os.remove(ORIGINAL_RULES_CSV_PATH)
        if os.path.exists(TEST_RULES_CSV_PATH): # If a test created this directly
            os.remove(TEST_RULES_CSV_PATH)

        # Restore original rules.csv if it was backed up
        if self.original_rules_existed:
            if os.path.exists(self.backup_rules_csv_path):
                 os.rename(self.backup_rules_csv_path, ORIGINAL_RULES_CSV_PATH)
        elif os.path.exists(ORIGINAL_RULES_CSV_PATH): # If no original but one was created by test
             pass # Should be handled by the first os.remove

    def create_dummy_csv(self, file_path, rules_data):
        """Helper function to create a CSV file with given rules."""
        with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['pattern', 'response']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for pattern, response in rules_data.items():
                writer.writerow({'pattern': pattern, 'response': response})

    def test_load_rules_from_csv(self):
        """Test loading rules from a CSV file."""
        test_rules_data = {
            "hello": "Hi there from test CSV!",
            "test question": "Test answer."
        }
        self.create_dummy_csv(TEST_RULES_CSV_PATH, test_rules_data)

        loaded_rules = load_rules_from_csv(TEST_RULES_CSV_PATH)

        # Expect patterns to be lowercased by load_rules_from_csv
        expected_rules = {k.lower(): v for k, v in test_rules_data.items()}
        self.assertEqual(loaded_rules, expected_rules)

    def test_load_rules_from_nonexistent_csv(self):
        """Test loading rules from a non-existent CSV file."""
        # Ensure the file does not exist before calling
        if os.path.exists("non_existent_rules.csv"):
            os.remove("non_existent_rules.csv")

        loaded_rules = load_rules_from_csv("non_existent_rules.csv")
        self.assertEqual(loaded_rules, {}) # Expect an empty dict

    @patch('chatbot.integrations.gemini_client.get_gemini_response')
    def test_get_response_matching_rule(self, mock_get_gemini_response):
        """Test get_response when a rule is matched."""
        test_rules_data = {"howdy": "Partner!"}
        # Create rules.csv for the core_chatbot to load
        self.create_dummy_csv(ORIGINAL_RULES_CSV_PATH, test_rules_data)

        # The core_chatbot.rules is loaded at import time.
        # We need to make it reload the rules or update its global 'rules' variable.
        core_chatbot.rules = load_rules_from_csv(ORIGINAL_RULES_CSV_PATH)

        response = get_response("howdy")
        self.assertEqual(response, "Partner!")
        mock_get_gemini_response.assert_not_called()

    @patch('chatbot.integrations.gemini_client.get_gemini_response')
    def test_get_response_no_rule_match_calls_gemini(self, mock_get_gemini_response):
        """Test get_response calls Gemini client when no rule matches."""
        # Setup: Ensure rules.csv is empty or has non-matching rules
        self.create_dummy_csv(ORIGINAL_RULES_CSV_PATH, {"greeting": "hello there"})
        core_chatbot.rules = load_rules_from_csv(ORIGINAL_RULES_CSV_PATH)

        mock_gemini_msg = "Gemini says hi to unknown input"
        mock_get_gemini_response.return_value = mock_gemini_msg

        user_input = "some unknown phrase"
        response = get_response(user_input)

        self.assertEqual(response, mock_gemini_msg)
        mock_get_gemini_response.assert_called_once_with(user_input)

    @patch('chatbot.integrations.gemini_client.get_gemini_response')
    def test_get_response_empty_rules_csv_calls_gemini(self, mock_get_gemini_response):
        """Test get_response with an empty rules.csv file."""
        # Create an empty rules.csv (only headers)
        with open(ORIGINAL_RULES_CSV_PATH, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['pattern', 'response'])
        core_chatbot.rules = load_rules_from_csv(ORIGINAL_RULES_CSV_PATH) # Reload to get empty rules

        mock_gemini_msg = "Gemini handles empty rules"
        mock_get_gemini_response.return_value = mock_gemini_msg

        user_input = "anything"
        response = get_response(user_input)

        self.assertEqual(response, mock_gemini_msg)
        mock_get_gemini_response.assert_called_once_with(user_input)


if __name__ == '__main__':
    # Ensure the script can be run directly and find modules
    # This is a more robust way for __main__ but tests are usually run by a test runner
    # If running `python tests/test_chatbot_logic.py` from project root, PROJECT_ROOT should be correct.
    # If running from `chatbot/tests` dir, it should also be correct.
    print(f"Running tests with PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"Current sys.path: {sys.path}")
    if 'chatbot.core' not in sys.modules:
         print("Warning: chatbot.core may not be loaded yet if there were prior import errors.")

    unittest.main()
