import csv
import os
# Ensure this path is correct if gemini_client is used as a fallback
# Assuming gemini_client.py is in chatbot/chatbot/integrations/
# And this file is in chatbot/chatbot/core/
# So, from core, integrations is a sibling of core, under the parent 'chatbot' (the second one)
# The project root for app.py is one level above the parent 'chatbot'
# This pathing can be tricky.

# When run via `python -m chatbot.chatbot.web.app` from project_root:
# project_root/chatbot/chatbot/web/app.py
# project_root/chatbot/chatbot/core/rules_based_chatbot.py
# project_root/chatbot/chatbot/integrations/gemini_client.py
# So the import should be from chatbot.chatbot.integrations.gemini_client
from chatbot.chatbot.integrations.gemini_client import get_gemini_response

# Determine Project Root (common way for data file access)
# This file is in chatbot/chatbot/core/rules_based_chatbot.py
# Project root is three levels up. (/app)
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
RULES_CSV_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'data', 'rules.csv')

class RulesBasedChatbot:
    def __init__(self):
        self.rules = {} # Initialize rules as empty dict before loading
        self._load_rules_from_csv() # Call load_rules to populate self.rules
        if not self.rules:
            print("WARNING (RulesBasedChatbot): No rules were loaded. Chatbot will rely on Gemini.")
        else:
            print(f"INFO (RulesBasedChatbot): Loaded {len(self.rules)} rules.")
            # print(f"DEBUG (RulesBasedChatbot): Loaded rules keys: {list(self.rules.keys())}") # Potentially very verbose

    def _load_rules_from_csv(self):
        # self.rules is used directly here, not a local 'rules' variable that shadows it.
        print(f"DEBUG (RulesBasedChatbot): Attempting to load rules from: {RULES_CSV_FILE_PATH}")
        try:
            # Ensure rules.csv exists with headers, otherwise create it
            if not os.path.exists(RULES_CSV_FILE_PATH):
                print(f"DEBUG (RulesBasedChatbot): {RULES_CSV_FILE_PATH} not found. Creating with headers.")
                os.makedirs(os.path.dirname(RULES_CSV_FILE_PATH), exist_ok=True)
                with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['pattern', 'response'])
                # self.rules remains empty as file was just created
                return

            with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Validate headers
                if not reader.fieldnames or 'pattern' not in reader.fieldnames or 'response' not in reader.fieldnames:
                    print(f"ERROR (RulesBasedChatbot): CSV file {RULES_CSV_FILE_PATH} is missing 'pattern' or 'response' headers. Fieldnames found: {reader.fieldnames}")
                    # self.rules remains empty or as previously loaded if any error
                    return

                temp_rules = {} # Load into a temporary dict first
                print("DEBUG (RulesBasedChatbot): Loading patterns from CSV...")
                for i, row in enumerate(reader):
                    pattern = row.get('pattern')
                    response = row.get('response')
                    if pattern and response is not None: # response can be an empty string
                        processed_pattern = pattern.lower().strip()
                        if not processed_pattern: # Skip if pattern is empty after processing
                            print(f"WARNING (RulesBasedChatbot): Skipped row #{i+1} in CSV due to empty pattern after processing.")
                            continue
                        temp_rules[processed_pattern] = response.strip() # Store with stripped response too
                        # print(f"DEBUG (RulesBasedChatbot): Loaded rule #{i+1}: PATTERN='{processed_pattern}' => RESPONSE='{response[:50]}...' (stripped)") # Verbose
                    else:
                        print(f"WARNING (RulesBasedChatbot): Skipped row #{i+1} in CSV due to missing pattern or response field.")
                self.rules = temp_rules # Assign to instance variable after successful load
            print(f"DEBUG (RulesBasedChatbot): Finished loading {len(self.rules)} rules from CSV.")
        except FileNotFoundError: # Should be caught by os.path.exists, but as a safeguard
            print(f"ERROR (RulesBasedChatbot): Rules file not found at {RULES_CSV_FILE_PATH} during read. No rules loaded.")
        except Exception as e:
            print(f"ERROR (RulesBasedChatbot): Could not load rules from CSV: {e}")
        # Ensure self.rules is a dict even if loading fails badly
        if not isinstance(self.rules, dict):
            self.rules = {}


    def get_response(self, user_input: str) -> str:
        processed_input = user_input.lower().strip()
        print(f"DEBUG (RulesBasedChatbot): Received user_input='{user_input}', processed_input='{processed_input}'")
        # print(f"DEBUG (RulesBasedChatbot): Checking against {len(self.rules)} loaded rule patterns.") # Less useful than specific checks

        # Exact match first (more specific)
        if processed_input in self.rules:
            response = self.rules[processed_input]
            print(f"DEBUG (RulesBasedChatbot): Exact match found for pattern='{processed_input}'. Response='{response[:70]}...'")
            return response

        # Substring match (less specific)
        for pattern_key, response_val in self.rules.items():
            # pattern_key is already lowercased and stripped
            # print(f"DEBUG (RulesBasedChatbot): Checking substring: IS '{pattern_key}' IN '{processed_input}'?" ) # Very verbose
            if pattern_key in processed_input:
                print(f"DEBUG (RulesBasedChatbot): Substring match found for pattern='{pattern_key}' in input='{processed_input}'. Response='{response_val[:70]}...'")
                return response_val

        print(f"INFO (RulesBasedChatbot): No rule matched for '{processed_input}'. Calling Gemini...")
        # Fallback to Gemini if no rule matches
        return get_gemini_response(user_input) # Pass original user_input to Gemini


_chatbot_instance = None

def get_chatbot_instance():
    global _chatbot_instance
    if _chatbot_instance is None:
        print("INFO (RulesBasedChatbot Module): Creating new RulesBasedChatbot instance.")
        _chatbot_instance = RulesBasedChatbot()
    # TODO: Add logic here for re-loading rules if rules.csv has changed since last load.
    # For now, it loads rules once per instance creation.
    return _chatbot_instance

# This is the function app.py will call
def get_response(user_input: str) -> str:
    chatbot = get_chatbot_instance() # Ensures a single instance is used
    return chatbot.get_response(user_input) # Call method on the instance

# Example of direct execution (for testing this module itself)
if __name__ == '__main__':
    print("--- Direct execution of rules_based_chatbot.py ---")
    # Ensure rules.csv has some sample data for this test to be meaningful
    # e.g., pattern "hello", response "Hi there from rules.csv!"
    #       pattern "test rule", response "This is a test response from CSV."

    # Create a dummy rules.csv for testing if it doesn't exist or is empty
    if not os.path.exists(RULES_CSV_FILE_PATH) or os.path.getsize(RULES_CSV_FILE_PATH) < 20: # arbitrary small size
        print(f"INFO (__main__): Creating/Overwriting {RULES_CSV_FILE_PATH} with sample rules for testing.")
        os.makedirs(os.path.dirname(RULES_CSV_FILE_PATH), exist_ok=True)
        with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['pattern', 'response'])
            writer.writerow(['hello', 'Hi there from rules.csv!'])
            writer.writerow(['test rule', 'This is a test response from CSV.'])
            writer.writerow(['tell me a joke', 'Why did the chicken cross the road? To get to the other side! (from CSV)'])

    print("\nInitializing chatbot instance for test...")
    test_bot = get_chatbot_instance() # Uses the singleton accessor

    print("\n--- Testing rule matching ---")
    test_inputs = ["hello", "This is a test RULE.", "Tell me something else", "tell me a joke"]
    for text_in in test_inputs:
        print(f"\nInput: \"{text_in}\"")
        response_out = test_bot.get_response(text_in) # Call method on the instance
        print(f"Output: \"{response_out}\"")

    print("\n--- Testing with an input likely to go to Gemini ---")
    gemini_test_input = "What is the airspeed velocity of an unladen swallow?"
    print(f"Input: \"{gemini_test_input}\"")
    gemini_response = test_bot.get_response(gemini_test_input)
    print(f"Output (from Gemini via chatbot): \"{gemini_response}\"")
    print("\n--- End of direct execution test ---")
