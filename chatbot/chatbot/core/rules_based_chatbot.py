import csv
import os
from flask import session # For session management

# Assuming gemini_client.py is in chatbot/chatbot/integrations/
from chatbot.chatbot.integrations.gemini_client import get_gemini_response

# Determine Project Root for data file access
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
RULES_CSV_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'data', 'rules.csv')

EXPECTED_CSV_HEADERS = ['Rule_ID', 'Context_Required', 'Pattern', 'Response', 'Set_Context_On_Response', 'GoTo_Rule_ID']

class RulesBasedChatbot:
    def __init__(self):
        self.rules_list = []  # Stores rules as a list of dicts, preserving order
        self.rules_by_id = {} # Stores rules by Rule_ID for quick GoTo lookups
        self._load_rules_from_csv()
        if not self.rules_list:
            print("WARNING (RulesBasedChatbot): No rules were loaded. Chatbot will rely on Gemini.")
        else:
            print(f"INFO (RulesBasedChatbot): Loaded {len(self.rules_list)} rules.")

    def _ensure_csv_headers(self):
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(RULES_CSV_FILE_PATH), exist_ok=True)
        if not os.path.exists(RULES_CSV_FILE_PATH) or os.path.getsize(RULES_CSV_FILE_PATH) == 0:
            print(f"DEBUG (RulesBasedChatbot): {RULES_CSV_FILE_PATH} not found or empty. Creating with headers.")
            with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(EXPECTED_CSV_HEADERS)
            return True # File was created/headers written
        else:
            try:
                with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    # Normalize headers for comparison (lower, strip)
                    normalized_headers = [h.strip().lower() for h in headers] if headers else []
                    normalized_expected_headers = [eh.strip().lower() for eh in EXPECTED_CSV_HEADERS]
                    if not headers or normalized_headers != normalized_expected_headers:
                        print(f"WARNING (RulesBasedChatbot): CSV file {RULES_CSV_FILE_PATH} has incorrect or missing headers. Expected: {EXPECTED_CSV_HEADERS}, Found: {headers}")
                        return False # Headers are not as expected
                    return True # Headers are fine
            except Exception as e:
                print(f"ERROR (RulesBasedChatbot): Could not verify CSV headers: {e}")
                return False

    def _load_rules_from_csv(self):
        self.rules_list = []
        self.rules_by_id = {}
        print(f"DEBUG (RulesBasedChatbot): Attempting to load rules from: {RULES_CSV_FILE_PATH}")
        if not self._ensure_csv_headers():
            print("ERROR (RulesBasedChatbot): CSV header check failed. Rules not loaded.")
            return

        try:
            with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                current_fieldnames = reader.fieldnames if reader.fieldnames else []
                normalized_fieldnames = [fn.strip().lower() for fn in current_fieldnames]
                normalized_expected_headers = [eh.strip().lower() for eh in EXPECTED_CSV_HEADERS]

                if not current_fieldnames and os.path.getsize(RULES_CSV_FILE_PATH) > 0 :
                     print(f"ERROR (RulesBasedChatbot): CSV file {RULES_CSV_FILE_PATH} seems to be missing headers for DictReader. Fieldnames found: {current_fieldnames}")
                     return
                elif current_fieldnames and normalized_fieldnames != normalized_expected_headers:
                     print(f"ERROR (RulesBasedChatbot): CSV file {RULES_CSV_FILE_PATH} headers for DictReader do not match. Expected: {EXPECTED_CSV_HEADERS}, Found: {current_fieldnames}")
                     return

                print("DEBUG (RulesBasedChatbot): Loading rules from CSV with new structure...")
                for i, row in enumerate(reader):
                    try:
                        rule = {}
                        rule['Rule_ID'] = row.get('Rule_ID', '').strip()
                        rule['Context_Required'] = row.get('Context_Required', '').strip().lower() or None
                        rule['Pattern'] = row.get('Pattern', '').strip().lower()
                        rule['Response'] = row.get('Response', '').strip()
                        rule['Set_Context_On_Response'] = row.get('Set_Context_On_Response', '').strip().lower() or None
                        rule['GoTo_Rule_ID'] = row.get('GoTo_Rule_ID', '').strip() or None

                        if not rule['Rule_ID'] or not rule['Pattern']:
                            if not rule['Rule_ID']:
                                print(f"WARNING (RulesBasedChatbot): Skipped row #{i+1} in CSV due to missing Rule_ID.")
                                continue
                            if not rule['Pattern'] and not rule['Context_Required']:
                                print(f"WARNING (RulesBasedChatbot): Skipped row #{i+1} (Rule ID: {rule['Rule_ID']}) due to missing Pattern when no Context_Required is set.")
                                continue

                        self.rules_list.append(rule)
                        self.rules_by_id[rule['Rule_ID']] = rule
                    except Exception as e_row:
                        print(f"ERROR (RulesBasedChatbot): Failed to process row #{i+1}: {row}. Error: {e_row}")
            print(f"DEBUG (RulesBasedChatbot): Finished loading {len(self.rules_list)} rules into rules_list and {len(self.rules_by_id)} into rules_by_id.")
        except FileNotFoundError:
            print(f"ERROR (RulesBasedChatbot): Rules file not found at {RULES_CSV_FILE_PATH}. Should have been created by _ensure_csv_headers.")
        except Exception as e:
            print(f"ERROR (RulesBasedChatbot): Could not load rules from CSV: {e}")

    def _find_matching_rule(self, current_input, current_context):
        print(f"DEBUG (RulesBasedChatbot): _find_matching_rule: input='{current_input}', context='{current_context}'")
        for rule in self.rules_list:
            pattern_match = rule['Pattern'] == '*' or (rule['Pattern'] and rule['Pattern'] in current_input)
            context_match = rule['Context_Required'] == current_context
            if context_match and pattern_match:
                print(f"DEBUG (RulesBasedChatbot): Contextual match found: Rule ID '{rule['Rule_ID']}'")
                return rule

        for rule in self.rules_list:
            pattern_match = rule['Pattern'] == '*' or (rule['Pattern'] and rule['Pattern'] in current_input)
            if not rule['Context_Required'] and pattern_match:
                print(f"DEBUG (RulesBasedChatbot): General match found: Rule ID '{rule['Rule_ID']}'")
                return rule
        return None

    def get_response(self, user_input: str, current_session) -> str:
        processed_input = user_input.lower().strip()
        current_context = current_session.get('chatbot_context')

        print(f"DEBUG (RulesBasedChatbot): get_response - User Input='{user_input}', Processed='{processed_input}', Context='{current_context}'")

        final_response_parts = []
        next_rule_id_to_process = None
        max_goto_loops = 5
        loops = 0
        visited_rules_in_chain = set()

        matched_rule = self._find_matching_rule(processed_input, current_context)

        if matched_rule:
            print(f"DEBUG (RulesBasedChatbot): Initial match: Rule ID '{matched_rule['Rule_ID']}' with response '{matched_rule['Response'][:50]}...' ")
            if matched_rule['Response']:
                 final_response_parts.append(matched_rule['Response'])

            visited_rules_in_chain.add(matched_rule['Rule_ID'])

            if matched_rule.get('Set_Context_On_Response') == 'clear' or matched_rule.get('Set_Context_On_Response') == '':
                if current_session.get('chatbot_context') is not None:
                    print(f"DEBUG (RulesBasedChatbot): Context CLEARED by Rule ID '{matched_rule['Rule_ID']}'.")
                current_session.pop('chatbot_context', None)
            elif matched_rule.get('Set_Context_On_Response'):
                if current_session.get('chatbot_context') != matched_rule['Set_Context_On_Response']:
                    print(f"DEBUG (RulesBasedChatbot): Context SET to '{matched_rule['Set_Context_On_Response']}' by Rule ID '{matched_rule['Rule_ID']}'.")
                current_session['chatbot_context'] = matched_rule['Set_Context_On_Response']

            next_rule_id_to_process = matched_rule.get('GoTo_Rule_ID')
        else:
            print(f"INFO (RulesBasedChatbot): No initial rule matched for '{processed_input}' with context '{current_context}'. Fallback to Gemini.")
            if current_session.get('chatbot_context') is not None:
                 print(f"DEBUG (RulesBasedChatbot): Clearing context before Gemini call.")
            current_session.pop('chatbot_context', None)
            return get_gemini_response(user_input)

        while next_rule_id_to_process and loops < max_goto_loops:
            loops += 1
            if next_rule_id_to_process in visited_rules_in_chain:
                print(f"WARNING (RulesBasedChatbot): Detected loop in GoTo chain involving Rule ID '{next_rule_id_to_process}'. Ending chain.")
                break
            visited_rules_in_chain.add(next_rule_id_to_process)

            print(f"DEBUG (RulesBasedChatbot): Processing GoTo_Rule_ID: '{next_rule_id_to_process}', Loop: {loops}")
            goto_rule = self.rules_by_id.get(next_rule_id_to_process)
            if goto_rule:
                if goto_rule['Response']:
                    final_response_parts.append(goto_rule['Response'])
                print(f"DEBUG (RulesBasedChatbot): GoTo Rule ID '{goto_rule['Rule_ID']}' adding response: '{goto_rule['Response'][:50]}...' ")

                if goto_rule.get('Set_Context_On_Response') == 'clear' or goto_rule.get('Set_Context_On_Response') == '':
                    if current_session.get('chatbot_context') is not None:
                         print(f"DEBUG (RulesBasedChatbot): Context CLEARED by GoTo Rule ID '{goto_rule['Rule_ID']}'.")
                    current_session.pop('chatbot_context', None)
                elif goto_rule.get('Set_Context_On_Response'):
                    if current_session.get('chatbot_context') != goto_rule['Set_Context_On_Response']:
                        print(f"DEBUG (RulesBasedChatbot): Context SET to '{goto_rule['Set_Context_On_Response']}' by GoTo Rule ID '{goto_rule['Rule_ID']}'.")
                    current_session['chatbot_context'] = goto_rule['Set_Context_On_Response']

                next_rule_id_to_process = goto_rule.get('GoTo_Rule_ID')
                if not next_rule_id_to_process:
                    print(f"DEBUG (RulesBasedChatbot): GoTo chain ended at Rule ID '{goto_rule['Rule_ID']}'.")
                    break
            else:
                print(f"WARNING (RulesBasedChatbot): GoTo_Rule_ID '{next_rule_id_to_process}' not found. Ending GoTo chain.")
                break

        if loops >= max_goto_loops:
            print(f"WARNING (RulesBasedChatbot): Exceeded max GoTo loops ({max_goto_loops}). Ending chain.")

        if not final_response_parts:
            print(f"INFO (RulesBasedChatbot): Rule chain resulted in no response. Fallback to Gemini for input '{user_input}'.")
            if current_session.get('chatbot_context') is not None:
                 print(f"DEBUG (RulesBasedChatbot): Clearing context before Gemini call due to empty chain response.")
            current_session.pop('chatbot_context', None)
            return get_gemini_response(user_input)

        return "\\n".join(final_response_parts) # Join chained responses with literal newlines for HTML display

# --- Singleton Instance Management ---
_chatbot_instance = None

def get_chatbot_instance():
    global _chatbot_instance
    if _chatbot_instance is None:
        print("INFO (RulesBasedChatbot Module): Creating new RulesBasedChatbot singleton instance.")
        _chatbot_instance = RulesBasedChatbot()
    return _chatbot_instance

# This is the main function imported and used by app.py
def get_response_for_web(user_input: str) -> str:
    chatbot = get_chatbot_instance()
    # 'session' is Flask's session proxy, available in request context.
    return chatbot.get_response(user_input, session)

# --- Direct Test Block (for module-level testing) ---
if __name__ == '__main__':
    print("--- Direct Test of RulesBasedChatbot (New Threaded Logic) ---")

    # Create a dummy rules.csv for testing
    print(f"INFO (__main__): Creating/Overwriting dummy {RULES_CSV_FILE_PATH} for testing.")
    os.makedirs(os.path.dirname(RULES_CSV_FILE_PATH), exist_ok=True)
    with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(EXPECTED_CSV_HEADERS)
        # Rule_ID, Context_Required, Pattern, Response, Set_Context_On_Response, GoTo_Rule_ID
        writer.writerow(['1', '', 'hello', 'Hi there! How can I help you today?', 'greeted', ''])
        writer.writerow(['2', 'greeted', 'tell me a joke', 'Why did the scarecrow win an award?', '', 'JOKE_PUNCHLINE'])
        writer.writerow(['JOKE_PUNCHLINE', '', '', 'Because he was outstanding in his field!', 'joke_told', '']) # Chained rule, no pattern needed if directly GoTo'd
        writer.writerow(['3', 'greeted', 'what is your name', 'My name is Max, your virtual assistant.', '', ''])
        writer.writerow(['4', '', 'bye', 'Goodbye! Have a great day.', 'clear', '']) # 'clear' context
        writer.writerow(['5', '', 'chain_test_start', 'This is the first part of a chain.', 'chain_active', 'CHAIN_MIDDLE'])
        writer.writerow(['CHAIN_MIDDLE', 'chain_active', '', 'This is the middle part, context was required.', 'chain_middle_done', 'CHAIN_END']) # Pattern can be empty if context is key
        writer.writerow(['CHAIN_END', 'chain_middle_done', '', 'This is the end of the chain.', 'clear', ''])
        writer.writerow(['LOOP_A', '', 'loop_test', 'Loop A starts here.', 'loop_active', 'LOOP_B'])
        writer.writerow(['LOOP_B', 'loop_active', '', 'Loop B continues.', '', 'LOOP_A']) # This creates a GoTo loop

    # Mock Flask session for direct testing
    class MockSession(dict):
        def permanent(self, val=None): pass
        def pop(self, key, default=None):
            return super().pop(key, default)

    mock_session_for_test = MockSession()

    print("\\nInitializing chatbot instance for test...")
    test_bot = get_chatbot_instance()

    test_cases = [
        ("hello", "Initial greeting, sets context 'greeted'"),
        ("tell me a joke", "Uses 'greeted' context, chains to JOKE_PUNCHLINE, sets context 'joke_told'"),
        ("what is your name", "Uses 'greeted' context (still from first hello if not overwritten), no context change"),
        ("tell me a joke", "Context is 'greeted' (or last relevant context). If 'joke_told', this will be a new interaction."),
        ("chain_test_start", "Test GoTo chain and context changes"),
        ("loop_test", "Test GoTo loop detection"),
        ("unknown input", "Test Gemini fallback after clearing context"),
        ("bye", "Clears context")
    ]

    for text, desc in test_cases:
        print(f"\\n--- Test Case: {desc} ---")
        print(f"User > {text} (Context before: {mock_session_for_test.get('chatbot_context')})")
        # In direct test, pass the mock_session_for_test to the main get_response method of the instance
        response = test_bot.get_response(text, mock_session_for_test)
        # For web, app.py would call get_response_for_web(text) which uses the actual Flask session
        print(f"Bot  > {response.replace(chr(10), ' | ') if isinstance(response, str) else response}") # Replace newlines for compact log
        print(f"(Context after: {mock_session_for_test.get('chatbot_context')})")

    print("\\n--- End of direct execution test ---")
