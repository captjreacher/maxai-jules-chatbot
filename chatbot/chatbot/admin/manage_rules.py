# chatbot/admin/manage_rules.py
import csv
import os

# Define the path to the rules.csv file relative to this script's location
# This makes the script more portable assuming a consistent project structure.
# __file__ is the path to the current script.
# os.path.dirname(__file__) is the directory of the current script (admin).
# os.path.join(..., "..", "data", "rules.csv") goes up one level, then into data, then rules.csv.
RULES_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "rules.csv")

def add_rule_to_csv(pattern: str, response: str):
    """
    Adds a new rule (pattern and response pair) to the rules.csv file.

    Args:
        pattern: The pattern string for the rule.
        response: The response string for the rule.
    """
    # Ensure the directory exists (it should, based on previous steps)
    os.makedirs(os.path.dirname(RULES_FILE_PATH), exist_ok=True)

    file_exists = os.path.isfile(RULES_FILE_PATH)

    with open(RULES_FILE_PATH, mode='a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['pattern', 'response']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists or os.path.getsize(RULES_FILE_PATH) == 0:
            writer.writeheader()  # Write header only if file is new or empty

        writer.writerow({'pattern': pattern, 'response': response})
    print(f"Rule added: '{pattern}' -> '{response}' to {RULES_FILE_PATH}")

if __name__ == '__main__':
    print("Rule Management Admin")
    print("---------------------")
    try:
        new_pattern = input("Enter the pattern for the new rule: ")
        new_response = input("Enter the response for this pattern: ")

        if not new_pattern or not new_response:
            print("Pattern and response cannot be empty. Rule not added.")
        else:
            add_rule_to_csv(new_pattern, new_response)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting.")
    except Exception as e:
        print(f"An error occurred: {e}")
