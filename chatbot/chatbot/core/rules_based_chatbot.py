# chatbot/core/rules_based_chatbot.py

import csv
import os
from chatbot.integrations.gemini_client import get_gemini_response

# Define the path to the rules.csv file relative to this script's location
RULES_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "rules.csv")

def load_rules_from_csv(file_path: str) -> dict:
    """
    Loads rules from a CSV file.

    Args:
        file_path: The path to the CSV file.

    Returns:
        A dictionary where keys are patterns and values are responses.
        Returns an empty dictionary if the file is not found or is empty.
    """
    loaded_rules = {}
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Ensure pattern and response are not None and are strings
                pattern = row.get('pattern', '').strip()
                response = row.get('response', '').strip()
                if pattern: # Only add rule if pattern is not empty
                    loaded_rules[pattern.lower()] = response # Store patterns in lowercase for case-insensitive matching
    except FileNotFoundError:
        print(f"Warning: Rules file not found at {file_path}. No rules loaded.")
    except Exception as e:
        print(f"Error loading rules from {file_path}: {e}")
    return loaded_rules

# Load rules at startup
rules = load_rules_from_csv(RULES_FILE_PATH)
if not rules:
    print("No rules were loaded. Chatbot may rely heavily on Gemini or default responses.")

# Comment out or remove the old hardcoded rules dictionary
# rules = {
# "hello": "Hi there!",
# "how are you": "I'm doing well, thank you for asking!",
# "what is your name": "I am a simple rule-based chatbot.",
# "bye": "Goodbye! Have a great day."
# }

def get_response(user_input: str) -> str:
    """
    Generates a response based on predefined rules.

    Args:
        user_input: The input string from the user.

    Returns:
        A string response from the chatbot, or a default message if no rule matches.
    """
    user_input_lower = user_input.lower()
    # Use the globally loaded 'rules' dictionary
    for pattern, response in rules.items():
        # .items() is already used correctly if rules is a dict
        if pattern in user_input_lower: # pattern is already lowercased during loading
            return response
    print(f"DEBUG: rules_based_chatbot.py - No rule matched for '{user_input}'. Calling Gemini...")
    return get_gemini_response(user_input)

if __name__ == '__main__':
    if not rules: # If rules are empty (e.g. file not found, or empty file)
        print("Warning: No rules loaded. The chatbot will rely on the Gemini integration.")

    # Ensure correct module loading if running directly from core
    # This setup assumes that the script might be run directly,
    # and adjusts sys.path to allow imports from the parent 'chatbot' directory.
    if not os.path.basename(os.getcwd()) == 'chatbot' and 'chatbot.integrations' not in sys.modules:
        # This means we are likely in chatbot/core or chatbot/
        # We need to ensure 'chatbot' parent directory is in path to find 'chatbot.integrations'
        # This is a common issue when running scripts within a package directly.
        # A better long-term solution is to run the chatbot as a module from the project root, e.g., python -m chatbot.core.rules_based_chatbot
        import sys
        # current_dir = os.path.dirname(os.path.abspath(__file__)) # core
        # parent_dir = os.path.dirname(current_dir) # chatbot
        # project_root = os.path.dirname(parent_dir) # directory containing chatbot
        # if project_root not in sys.path:
        #    sys.path.insert(0, project_root)
        # The above path adjustment is often needed. For now, let's assume PYTHONPATH is set or running as module.

    print("Chatbot initialized. Type 'bye' to exit.")
    while True:
        user_message = input("You: ")
        response = get_response(user_message)
        print(f"Chatbot: {response}")

        # Check if the matched response is the one for 'bye'
        # This requires 'bye' to be a pattern in rules.csv and loaded correctly
        bye_pattern = "bye" # Assuming 'bye' is the pattern string for exiting
        if bye_pattern in rules and user_message.lower() == bye_pattern and response == rules[bye_pattern]:
            break
        elif not rules and user_message.lower() == bye_pattern: # If no rules, 'bye' might be handled by Gemini
             # This case might need more specific handling if Gemini can also signal an exit.
             # For now, if rules are empty, 'bye' will just be another query to Gemini unless explicitly handled.
             # To ensure 'bye' works even without rules.csv, it could be a hardcoded check outside get_response.
             # However, the goal is to make rules data-driven.
             # A simple solution if 'bye' must always work:
            if user_message.lower() == 'bye': # Fallback bye if not in rules
                print("Chatbot: Goodbye! Have a great day.") # Default bye response
                break
