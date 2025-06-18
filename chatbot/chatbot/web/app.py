import os
import sys
from flask import Flask, render_template, request, session
from dotenv import load_dotenv

PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
dotenv_path = os.path.join(PROJECT_ROOT_DIR, '.env')
if os.path.exists(dotenv_path):
    print(f"INFO (app.py): Loading .env file from {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"WARNING (app.py): .env file not found at {dotenv_path}. Trying CWD.")
    if not load_dotenv():
        print("WARNING (app.py): .env file not found at CWD either. Some features might not work.")

if PROJECT_ROOT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_DIR)

try:
    from chatbot.chatbot.core.rules_based_chatbot import get_response_for_web as get_response
    from chatbot.chatbot.web.admin_views import admin_bp
except ImportError as e:
    print(f"ERROR (app.py): Failed to import necessary modules: {e}")
    def get_response(user_message): return f"ERROR: Chatbot core logic failed to load: {e}"
    admin_bp = None

app = Flask(__name__)

FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
if not FLASK_SECRET_KEY:
    print("WARNING (app.py): FLASK_SECRET_KEY not set in .env. Using temporary key.")
    app.secret_key = os.urandom(32)
else:
    app.secret_key = FLASK_SECRET_KEY
    print("INFO (app.py): Flask secret key loaded from .env.")

if admin_bp:
    app.register_blueprint(admin_bp)
    print("INFO (app.py): Admin blueprint registered.")
else:
    print("ERROR (app.py): Admin blueprint not registered due to import failure.")

conversation_history = []

@app.route('/', methods=['GET', 'POST'])
def chat_interface():
    if request.method == 'POST':
        user_message = request.form.get('message', '').strip()
        if user_message:
            print(f"DEBUG: app.py - User message: {user_message}")
            bot_response_text = get_response(user_message)
            print(f"DEBUG: app.py - Received bot_response: {bot_response_text}")
            conversation_history.append({'sender': 'User', 'text': user_message})
            conversation_history.append({'sender': 'Bot', 'text': bot_response_text})
    return render_template('index.html', conversation=list(conversation_history))

if __name__ == '__main__':
    print("INFO (app.py): Starting Flask development server.")
    app.run(debug=True, host='0.0.0.0', port=5000)