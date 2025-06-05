# chatbot/web/app.py
import sys
import os
from flask import Flask, render_template, request

# Adjust sys.path to include the parent directory (chatbot)
# This allows Flask to find the 'chatbot.core' module
# __file__ is chatbot/web/app.py
# os.path.dirname(__file__) is chatbot/web
# os.path.dirname(os.path.dirname(__file__)) is chatbot (the project's chatbot directory)
# This assumes the 'chatbot' directory itself is the root for module resolution for this project.
# If your project root is one level higher (e.g. a directory containing the 'chatbot' dir), adjust accordingly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from chatbot.core.rules_based_chatbot import get_response, rules as loaded_rules
except ImportError as e:
    print(f"Error importing chatbot.core.rules_based_chatbot: {e}")
    print("Please ensure that the 'chatbot' directory (the one containing core, web, etc.) is in your PYTHONPATH.")
    print(f"PROJECT_ROOT determined as: {PROJECT_ROOT}")
    print(f"sys.path: {sys.path}")
    # Define a fallback get_response if import fails, so Flask app can still start to show errors
    def get_response(user_input):
        return "ERROR: Chatbot core not loaded. Please check server logs."
    loaded_rules = {} # and empty rules

app = Flask(__name__) # Looks for templates in a 'templates' folder in the same directory as app.py

# Store conversation history in a simple list (for demonstration purposes)
# In a real app, you might use a session or a database.
conversation = []

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        user_message = request.form.get('message')
        if user_message:
            bot_response = get_response(user_message)
            conversation.append({'user': user_message, 'bot': bot_response})
            # For 'bye' command, if it's a rule, we might want to clear conversation or add a special message
            if user_message.lower() == "bye" and "bye" in loaded_rules and loaded_rules["bye"] == bot_response:
                # Optionally, you could clear conversation or add a "Session ended" message
                pass
    # Pass a copy of the conversation to avoid modification issues if any
    return render_template('index.html', conversation=list(conversation))

if __name__ == '__main__':
    print(f"Attempting to run Flask app. Ensure 'chatbot.core' can be imported.")
    print(f"PROJECT_ROOT for module resolution: {PROJECT_ROOT}")
    print(f"Current sys.path: {sys.path}")
    if 'chatbot.core.rules_based_chatbot' not in sys.modules:
        print("Warning: 'chatbot.core.rules_based_chatbot' not found in sys.modules before app.run().")
        print("If you see import errors from Flask, the path adjustment might not be correct for your environment.")
    app.run(debug=True, host='0.0.0.0', port=5000)
