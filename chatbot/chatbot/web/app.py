import os
import sys
import json # For loading appearance settings
from flask import Flask, render_template, request, session, url_for # session and url_for might be needed if chat evolves
from dotenv import load_dotenv

# --- Configuration & Path Setup ---
# This file: /app/chatbot/chatbot/web/app.py
# Project Root: /app
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DOTENV_PATH = os.path.join(PROJECT_ROOT_DIR, '.env')
APPEARANCE_SETTINGS_JSON_PATH = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'web', 'appearance_settings.json')

DEFAULT_APPEARANCE_SETTINGS = {
    "chat_window_bg_color": "#f0f0f0",
    "user_bubble_bg_color": "#007bff",
    "user_bubble_font_color": "#ffffff",
    "bot_bubble_bg_color": "#e9e9eb",
    "bot_bubble_font_color": "#333333",
    "font_family": "Arial, sans-serif",
    "chat_window_width": "400px",
    "chat_window_height": "600px",
    "header_bg_color": "#007bff",
    "header_font_color": "#ffffff",
    "input_bg_color": "#ffffff",
    "send_button_bg_color": "#007bff",
    "send_button_font_color": "#ffffff"
}

# Load .env file from project root
if os.path.exists(DOTENV_PATH):
    print(f"INFO (app.py): Loading .env file from {DOTENV_PATH}")
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    # Fallback to default search (e.g., CWD) if .env not found at determined project root
    if load_dotenv():
        print("INFO (app.py): .env file loaded via default search (e.g., CWD).")
    else:
        print("WARNING (app.py): .env file not found. Required environment variables may be missing.")

# Ensure project root is in sys.path for consistent imports when run with `python -m chatbot.chatbot.web.app`
# The project root here is /app, which contains the first `chatbot` directory (the package)
if PROJECT_ROOT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_DIR)
    # print(f"INFO (app.py): Added project root {PROJECT_ROOT_DIR} to sys.path for module resolution.")

# --- Module Imports (after sys.path modification if any) ---
try:
    from chatbot.chatbot.core.rules_based_chatbot import get_response_for_web as get_response
    from chatbot.chatbot.web.admin_views import admin_bp
    modules_loaded_successfully = True
except ImportError as e:
    print(f"ERROR (app.py): Failed to import critical modules (rules_based_chatbot or admin_views): {e}")
    print("         Ensure the project structure is correct and all dependencies are installed.")
    # Define fallback get_response if core logic is missing
    def get_response(user_message): return f"ERROR: Chatbot core logic failed to load: {e}. Please check server logs."
    admin_bp = None # Ensure admin_bp is None if import fails
    modules_loaded_successfully = False

# --- Flask App Initialization ---
app = Flask(__name__) # Looks for /templates relative to this file's directory (web/templates)

# Configure Secret Key for session management (used by admin panel)
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
if not FLASK_SECRET_KEY:
    print("CRITICAL (app.py): FLASK_SECRET_KEY not set in .env. Using a temporary, insecure key. Sessions will NOT persist across restarts.")
    app.secret_key = os.urandom(32) # Highly recommended to set a persistent key in .env
else:
    app.secret_key = FLASK_SECRET_KEY
    print("INFO (app.py): Flask secret key loaded from .env.")

# Register Admin Blueprint
if admin_bp and modules_loaded_successfully: # Only register if import was successful
    app.register_blueprint(admin_bp)
    print("INFO (app.py): Admin blueprint registered successfully.")
else:
    print("ERROR (app.py): Admin blueprint not registered, likely due to import failure or it being None.")

# --- In-memory Conversation History (for demonstration) ---
# In a production app, consider using server-side sessions or a database for history.
conversation_history = []

# --- Helper for Appearance Settings ---
def _load_appearance_settings_for_chat():
    if os.path.exists(APPEARANCE_SETTINGS_JSON_PATH):
        try:
            with open(APPEARANCE_SETTINGS_JSON_PATH, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Ensure all default keys are present in loaded settings
                for key, value in DEFAULT_APPEARANCE_SETTINGS.items():
                    settings.setdefault(key, value)
                return settings
        except json.JSONDecodeError as e:
            print(f'ERROR (app.py): Failed to decode {APPEARANCE_SETTINGS_JSON_PATH}: {e}. Using default appearance settings.')
            return DEFAULT_APPEARANCE_SETTINGS.copy()
        except Exception as e: # Catch other potential errors like permission issues
            print(f'WARNING (app.py): Error loading {APPEARANCE_SETTINGS_JSON_PATH}: {e}. Using default appearance settings.')
            return DEFAULT_APPEARANCE_SETTINGS.copy()
    else: # File does not exist, create it with defaults
        print(f"INFO (app.py): {APPEARANCE_SETTINGS_JSON_PATH} not found. Creating with default settings.")
        try:
            os.makedirs(os.path.dirname(APPEARANCE_SETTINGS_JSON_PATH), exist_ok=True)
            with open(APPEARANCE_SETTINGS_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_APPEARANCE_SETTINGS, f, indent=4)
            return DEFAULT_APPEARANCE_SETTINGS.copy()
        except Exception as e:
            print(f"ERROR (app.py): Failed to create default {APPEARANCE_SETTINGS_JSON_PATH}: {e}. Using in-memory defaults.")
            return DEFAULT_APPEARANCE_SETTINGS.copy()


# --- Main Chat Route ---
@app.route('/', methods=['GET', 'POST'])
def chat_interface():
    if request.method == 'POST':
        user_message = request.form.get('message', '').strip()
        if user_message:
            # print(f"DEBUG (app.py): User message received: '{user_message}'") # Verbose
            if not modules_loaded_successfully: # Check if core logic is available
                 bot_response_text = "Chatbot core components failed to load. Please contact support."
            else:
                 bot_response_text = get_response(user_message) # Aliased to get_response_for_web
            # print(f"DEBUG (app.py): Bot response generated: '{bot_response_text[:60]}...'") # Verbose

            # Append to global history list
            conversation_history.append({'sender': 'User', 'text': user_message})
            conversation_history.append({'sender': 'Bot', 'text': bot_response_text})
            # Note: For multiple users, conversation_history should be session-based or user-specific.

    current_appearance = _load_appearance_settings_for_chat()
    # Pass a copy of the history to avoid issues if modifying it while rendering
    return render_template('index.html',
                           conversation=list(conversation_history),
                           appearance_settings=current_appearance)

# --- Run Application ---
if __name__ == '__main__':
    print("INFO (app.py): Starting Flask development server...")
    # Check for main template existence for better startup diagnostics
    main_template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    if not os.path.exists(main_template_path):
        print(f"CRITICAL (app.py): Main chat template 'index.html' not found at expected path: {main_template_path}")
        print("                 The application may not run correctly without this template.")

    app.run(debug=True, host='0.0.0.0', port=5000)
