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
        if not os.path.exists(RULES_CSV_FILE_PATH) or os.path.getsize(RULES_CSV_FILE_PATH) == 0:
            print(f"DEBUG (RulesBasedChatbot): {RULES_CSV_FILE_PATH} not found or empty. Creating with headers.")
            os.makedirs(os.path.dirname(RULES_CSV_FILE_PATH), exist_ok=True)
            with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(EXPECTED_CSV_HEADERS)
            return True # File was created/headers written
        else:
            try:
                with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    if not headers or [h.strip().lower() for h in headers] != [eh.strip().lower() for eh in EXPECTED_CSV_HEADERS]:
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

                        if not rule['Rule_ID']:
                            print(f"WARNING (RulesBasedChatbot): Skipped row #{i+1} in CSV due to missing Rule_ID.")
                            continue
                        
                        self.rules_list.append(rule)
                        self.rules_by_id[rule['Rule_ID']] = rule
                    except Exception as e_row:
                        print(f"ERROR (RulesBasedChatbot): Failed to process row #{i+1}: {row}. Error: {e_row}")
            print(f"DEBUG (RulesBasedChatbot): Finished loading {len(self.rules_list)} rules.")
        except FileNotFoundError:
            print(f"ERROR (RulesBasedChatbot): Rules file not found at {RULES_CSV_FILE_PATH}.")
        except Exception as e:
            print(f"ERROR (RulesBasedChatbot): Could not load rules from CSV: {e}")

    def _find_matching_rule(self, current_input, current_context):
        print(f"DEBUG (RulesBasedChatbot): _find_matching_rule: input='{current_input}', context='{current_context}'")
        
        for rule in self.rules_list:
            if rule['Context_Required'] == current_context:
                if not rule['Pattern'] or (rule['Pattern'] and rule['Pattern'] in current_input):
                    print(f"DEBUG (RulesBasedChatbot): Contextual match (pattern='{rule['Pattern']}'): Rule ID '{rule['Rule_ID']}'")
                    return rule
        
        for rule in self.rules_list:
            if not rule['Context_Required']:
                if rule['Pattern'] and rule['Pattern'] in current_input:
                    print(f"DEBUG (RulesBasedChatbot): General match (pattern='{rule['Pattern']}'): Rule ID '{rule['Rule_ID']}'")
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

        matched_rule = self._find_matching_rule(processed_input, current_context)

        current_rule_for_processing = matched_rule

        while current_rule_for_processing and loops < max_goto_loops:
            loops += 1 # Increment loop counter for the current rule being processed
            if loops > 1: # Log if this is part of a GoTo chain
                 print(f"DEBUG (RulesBasedChatbot): Processing GoTo_Rule_ID: '{current_rule_for_processing['Rule_ID']}', Loop: {loops-1}")
            else: # Initial match
                print(f"DEBUG (RulesBasedChatbot): Initial match: Rule ID '{current_rule_for_processing['Rule_ID']}'")

            if current_rule_for_processing['Response']:
                final_response_parts.append(current_rule_for_processing['Response'])
            print(f"DEBUG (RulesBasedChatbot): Rule ID '{current_rule_for_processing['Rule_ID']}' adding response: '{current_rule_for_processing['Response'][:50]}...' ")
            
            new_context = current_rule_for_processing.get('Set_Context_On_Response')
            if new_context:
                if new_context.upper() == 'CLEAR':
                    current_session.pop('chatbot_context', None)
                    print(f"DEBUG (RulesBasedChatbot): Context CLEARED by Rule ID '{current_rule_for_processing['Rule_ID']}'.")
                else:
                    current_session['chatbot_context'] = new_context
                    print(f"DEBUG (RulesBasedChatbot): Context SET to '{current_session['chatbot_context']}' by Rule ID '{current_rule_for_processing['Rule_ID']}'.")
            
            next_rule_id_to_process = current_rule_for_processing.get('GoTo_Rule_ID')
            if next_rule_id_to_process:
                current_rule_for_processing = self.rules_by_id.get(next_rule_id_to_process)
                if not current_rule_for_processing:
                    print(f"WARNING (RulesBasedChatbot): GoTo_Rule_ID '{next_rule_id_to_process}' not found. Ending GoTo chain.")
                    break # Exit while loop
            else:
                print(f"DEBUG (RulesBasedChatbot): No GoTo_Rule_ID from Rule ID '{current_rule_for_processing['Rule_ID']}'. Ending chain/response here.")
                break # Exit while loop
        
        if loops >= max_goto_loops:
            print(f"WARNING (RulesBasedChatbot): Exceeded max GoTo loops ({max_goto_loops}). Ending chain.")

        if not final_response_parts:
            # This case implies an initial match was not found or a GoTo chain led to no responses.
            if not matched_rule: # Only go to Gemini if there was no initial rule match at all.
                print(f"DEBUG (RulesBasedChatbot): No rule matched for '{processed_input}' with context '{current_context}'. Fallback to Gemini.")
                current_session.pop('chatbot_context', None) 
                return get_gemini_response(user_input)
            else: # A rule sequence was processed but yielded no response text (e.g. only GoTo and SetContext)
                print("DEBUG (RulesBasedChatbot): Rule sequence processed but no response text generated. Returning empty string or specific message.")
                return "Okay." # Or some other default if a rule chain gives no text

        return "\n".join(filter(None, final_response_parts))

_chatbot_instance = None

def get_chatbot_instance():
    global _chatbot_instance
    if _chatbot_instance is None:
        print("INFO (RulesBasedChatbot): Creating new RulesBasedChatbot singleton instance.")
        _chatbot_instance = RulesBasedChatbot()
    return _chatbot_instance

def get_response_for_web(user_input: str) -> str:
    chatbot = get_chatbot_instance()
    return chatbot.get_response(user_input, session) 

if __name__ == '__main__':
    print("--- Direct Test of RulesBasedChatbot (New Threaded Logic) ---")
    print(f"INFO (__main__): Ensuring dummy {RULES_CSV_FILE_PATH} for testing.")
    with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(EXPECTED_CSV_HEADERS)
        writer.writerow(['1', '', 'hello', 'Hi there! How are you?', 'greeted', ''])
        writer.writerow(['2', 'greeted', 'i am fine', 'Glad to hear it!', 'convo_positive', ''])
        writer.writerow(['3', 'greeted', 'not good', 'Oh no, sorry to hear that.', 'convo_negative', ''])
        writer.writerow(['4', '', 'chain_start', 'Starting chain...', 'chain_link1', '5'])
        writer.writerow(['5', '', '', 'Link 1 hit.', 'chain_link2', '6'])
        writer.writerow(['6', '', '', 'Link 2 hit. Chain ends.', 'CLEAR', ''])
        writer.writerow(['7', 'greeted', '', 'You said something while greeted, but I was expecting fine or not good.', 'greeted_catchall', ''])

    class MockSession(dict):
        def permanent(self, val=None): pass

    mock_session = MockSession()
    bot = RulesBasedChatbot() # New instance with dummy rules

    tests = [
        ("hello", "Hi there! How are you?", "greeted"),
        ("i am fine", "Glad to hear it!", "convo_positive"),
        ("hello", "Hi there! How are you?", "greeted"), # Reset context by new greeting
        ("not good", "Oh no, sorry to hear that.", "convo_negative"),
        ("hello again", "Hi there! How are you?", "greeted"), # Check if 'hello' in 'hello again' matches rule 1
        ("random stuff in greeted context", "You said something while greeted, but I was expecting fine or not good.", "greeted_catchall"), # Test context catch-all
        ("chain_start", "Starting chain...\nLink 1 hit.\nLink 2 hit. Chain ends.", "CLEAR"),
        ("anything after chain", "Fallback to Gemini expected", None) # Assuming Gemini returns this for unknown
    ]

    for (user_input, expected_response_start, expected_context_after) in tests:
        print(f"\nUser > {user_input} (Context before: {mock_session.get('chatbot_context')})")
        # Simulate Gemini fallback for the last test case for this direct test
        if user_input == "anything after chain":
            # Manually clear context as Gemini call would
            mock_session.pop('chatbot_context', None)
            response = get_gemini_response(user_input) 
        else:
            response = bot.get_response(user_input, mock_session)
        print(f"Bot  > {response}")
        print(f"(Context after: {mock_session.get('chatbot_context')}) - Expected: {expected_context_after}")
        assert mock_session.get('chatbot_context') == expected_context_after
        if user_input != "anything after chain": # Don't assert Gemini response here
            assert response.startswith(expected_response_start)

    print("\n--- Direct tests completed. ---")