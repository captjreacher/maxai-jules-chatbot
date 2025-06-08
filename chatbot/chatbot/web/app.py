import sys
import os # Ensure os is imported for app.secret_key
from flask import Flask, render_template, request
# Blueprint import should be after Flask, and before it's used.
# Assuming admin_views.py is in the same directory (chatbot/web) as app.py for this import style.
# The PROJECT_ROOT path adjustment should make 'chatbot.web' findable.
from chatbot.web.admin_views import admin_bp


# Adjust sys.path to allow importing from the parent directory (chatbot)
# This assumes 'app.py' is in 'chatbot/chatbot/web/' and 'core' is in 'chatbot/chatbot/core/'
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

# Secret key is crucial for session management, which admin login uses.
# IMPORTANT: For production, use a fixed, strong, randomly generated secret key stored securely (e.g., env var).
# Using os.urandom(24) generates a new key each time app restarts, invalidating old sessions. Good for dev, not prod.
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
if app.secret_key == os.urandom(24): # Check if fallback was used
    print("WARNING: FLASK_SECRET_KEY not set in .env, using a temporary session key. Sessions will not persist across restarts.")


# Register Blueprints
app.register_blueprint(admin_bp) # URLs from admin_bp (like /admin/login) are now active.

# Global or app context variable for conversation history
conversation = []

@app.route('/', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_message = request.form['message']
        print(f"DEBUG: app.py - User message: {user_message}")
        print(f"DEBUG: app.py - Calling get_response...")
        bot_response = get_response(user_message)
        print(f"DEBUG: app.py - Received bot_response: {bot_response}")
        conversation.append({'sender': 'User', 'text': user_message})
        conversation.append({'sender': 'Bot', 'text': bot_response})
    return render_template('index.html', conversation=list(conversation))

if __name__ == '__main__':
    print(f"Flask app __name__ is {__name__}")
    print(f"Flask app root_path is {app.root_path}")
    # To ensure dummy template creation works as intended if needed:
    templates_dir = os.path.join(app.root_path, 'templates') # app.root_path is chatbot/chatbot/web
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        print(f"Created missing templates directory: {templates_dir}")
        # This dummy index creation might conflict if admin templates are also in a sub-folder here.
        # The main index.html should be in chatbot/chatbot/web/templates/index.html
        # Admin templates are in chatbot/chatbot/web/templates/admin/
        dummy_index_path = os.path.join(templates_dir, 'index.html')
        if not os.path.exists(dummy_index_path): # Only create if main index.html is missing
            with open(dummy_index_path, 'w') as f_html:
                f_html.write("<h1>Fallback Template</h1><p>Dummy index.html created as it was missing.</p>")
                print(f"Created dummy index.html at {dummy_index_path}")

    # Note: Flask's default template loader looks in a "templates" folder relative to the app's root_path.
    # The admin blueprint's template_folder='admin' is relative to the app's template folder.
    # So, admin templates like 'admin/admin_login.html' are sought at '<app_template_dir>/admin/admin_login.html'.
    # This structure is: chatbot/chatbot/web/templates/admin/admin_login.html, which matches the script.

    app.run(debug=True, host='0.0.0.0', port=5000)

# Ensure lines from previous incorrect append are removed if they were there.
# The overwrite ensures this.
