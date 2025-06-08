import sys
import os
from flask import Flask, render_template, request

# Adjust sys.path to allow importing from the parent directory (chatbot)
# This assumes 'app.py' is in 'chatbot/chatbot/web/' and 'core' is in 'chatbot/chatbot/core/'
# We need to go up two levels from app.py to reach the project root 'chatbot/'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from chatbot.core.rules_based_chatbot import get_response
except ImportError as e:
    print(f"Error importing 'get_response': {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"PROJECT_ROOT used for import: {PROJECT_ROOT}")
    print(f"Current working directory: {os.getcwd()}")
    # Define a dummy get_response if the import fails
    def get_response(message):
        return f"Chatbot core logic error: Could not import 'get_response'. Details: {e}"

app = Flask(__name__) # Flask will look for templates in a 'templates' folder in the same dir as app.py
conversation = []

@app.route('/', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_message = request.form['message']
        print(f"DEBUG: app.py - User message: {user_message}")
        print(f"DEBUG: app.py - Calling get_response...")
        bot_response = get_response(user_message)
        print(f"DEBUG: app.py - Received bot_response: {bot_response}")
        conversation.append({'user': user_message, 'bot': bot_response})
    # Ensure the template is looked for in the correct relative path
    return render_template('index.html', conversation=list(conversation))

if __name__ == '__main__':
    # This ensures Flask looks for templates in 'chatbot/chatbot/web/templates'
    # by convention, if the app is in 'chatbot/chatbot/web/'
    print(f"Flask app __name__ is {__name__}")
    print(f"Flask app root_path is {app.root_path}")
    # To ensure dummy template creation works as intended if needed:
    templates_dir = os.path.join(app.root_path, 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        print(f"Created missing templates directory: {templates_dir}")
        dummy_index_path = os.path.join(templates_dir, 'index.html')
        if not os.path.exists(dummy_index_path):
            with open(dummy_index_path, 'w') as f_html:
                f_html.write("<h1>Fallback Template</h1><p>Dummy index.html created as it was missing.</p>")
                print(f"Created dummy index.html at {dummy_index_path}")

    app.run(debug=True, host='0.0.0.0', port=5000)
