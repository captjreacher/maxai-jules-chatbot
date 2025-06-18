import os
import functools
import csv
import json # Added for appearance settings
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DOTENV_PATH = os.path.join(PROJECT_ROOT_DIR, '.env')
RULES_CSV_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'data', 'rules.csv')
APPEARANCE_SETTINGS_JSON_PATH = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'web', 'appearance_settings.json') # Path to JSON
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'data', 'uploads')
ALLOWED_EXTENSIONS = {'csv'}
EXPECTED_CSV_HEADERS = ['Rule_ID', 'Context_Required', 'Pattern', 'Response', 'Set_Context_On_Response', 'GoTo_Rule_ID']

if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    if not load_dotenv():
        print("WARNING (admin_views): .env file not found. Admin auth and other .env dependent features may fail.")

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'password')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='../templates/admin')

# Import must be after Blueprint definition if admin_views is part of the same import cycle for app.py,
# but here it's a direct import for utility.
from chatbot.chatbot.core.rules_based_chatbot import get_chatbot_instance

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'admin_logged_in' not in session:
            flash('Please log in to access the admin panel.', 'warning')
            return redirect(url_for('admin.login', next=request.url))
        return view(**kwargs)
    return wrapped_view

def _ensure_csv_file_and_headers():
    # Ensure parent directory for RULES_CSV_FILE_PATH exists
    os.makedirs(os.path.dirname(RULES_CSV_FILE_PATH), exist_ok=True)
    file_exists = os.path.exists(RULES_CSV_FILE_PATH)
    is_empty = file_exists and os.path.getsize(RULES_CSV_FILE_PATH) == 0

    if not file_exists or is_empty:
        try:
            with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(EXPECTED_CSV_HEADERS)
            print(f"INFO (admin_views): {'Created' if not file_exists else 'Initialized empty'} rules.csv with headers.")
            return True
        except Exception as e:
            print(f'ERROR (admin_views): Error creating/initializing rules.csv: {e}')
            flash(f'Critical error: Could not create/initialize rules.csv: {e}', 'danger')
            return False
    else: # File exists and is not empty, verify headers
        try:
            with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                normalized_headers = [h.strip().lower() for h in headers]
                normalized_expected = [h.strip().lower() for h in EXPECTED_CSV_HEADERS]
                if normalized_headers != normalized_expected:
                    print(f"WARNING (admin_views): rules.csv headers mismatch. Expected: {EXPECTED_CSV_HEADERS}, Found: {headers}")
                    flash(f'WARNING: rules.csv headers are incorrect. Expected {EXPECTED_CSV_HEADERS}. Found {headers}. Operations may fail.', 'warning')
                    return False # Indicate header mismatch
            return True
        except Exception as e:
            print(f"ERROR (admin_views): Error verifying CSV headers: {e}")
            flash(f'Error verifying rules.csv headers: {e}', 'danger')
            return False

def _read_rules_from_csv():
    rules = []
    if not os.path.exists(RULES_CSV_FILE_PATH): # Check if file exists first
        _ensure_csv_file_and_headers() # Attempt to create it if it doesn't
        # If it still doesn't exist after attempt (e.g. permission error), then return empty
        if not os.path.exists(RULES_CSV_FILE_PATH):
             flash('rules.csv does not exist and could not be created.', 'danger')
             return rules

    try:
        with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Check headers using DictReader's fieldnames attribute
            normalized_expected_headers = [h.strip().lower() for h in EXPECTED_CSV_HEADERS]
            normalized_reader_fieldnames = [h.strip().lower() for h in reader.fieldnames] if reader.fieldnames else []
            if not reader.fieldnames or normalized_reader_fieldnames != normalized_expected_headers:
                 flash(f'WARNING: rules.csv headers are {reader.fieldnames if reader.fieldnames else "MISSING"}, expected {EXPECTED_CSV_HEADERS}. Cannot load rules reliably.', 'warning')
                 return []
            rules = list(reader)
    except Exception as e:
        flash(f'Error reading rules from rules.csv: {e}', 'danger')
    return rules

def _write_rules_to_csv(rules_list_of_dicts):
    try:
        _ensure_csv_file_and_headers() # Ensure directory exists and headers are fine before writing
        with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=EXPECTED_CSV_HEADERS, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rules_list_of_dicts)

        # Reload chatbot rules
        chatbot_instance = get_chatbot_instance()
        if chatbot_instance:
            chatbot_instance._load_rules_from_csv()
            flash('Rules saved and chatbot reloaded successfully.', 'success')
        else:
            flash('Rules saved, but chatbot instance not found for reloading.', 'warning')
        return True
    except Exception as e:
        flash(f'Error writing rules to rules.csv: {e}', 'danger')
        return False

DEFAULT_APPEARANCE_SETTINGS = {
    "chat_window_bg_color": "#f0f0f0", "user_bubble_bg_color": "#007bff",
    "user_bubble_font_color": "#ffffff", "bot_bubble_bg_color": "#e9e9eb",
    "bot_bubble_font_color": "#333333", "font_family": "Arial, sans-serif",
    "chat_window_width": "400px", "chat_window_height": "600px",
    "header_bg_color": "#007bff", "header_font_color": "#ffffff",
    "input_bg_color": "#ffffff", "send_button_bg_color": "#007bff",
    "send_button_font_color": "#ffffff"
}

def _load_appearance_settings():
    if not os.path.exists(APPEARANCE_SETTINGS_JSON_PATH):
        # If file doesn't exist, create it with defaults
        print(f"INFO: {APPEARANCE_SETTINGS_JSON_PATH} not found. Creating with default settings.")
        _save_appearance_settings(DEFAULT_APPEARANCE_SETTINGS.copy()) # Save defaults and this will flash success
        return DEFAULT_APPEARANCE_SETTINGS.copy()
    try:
        with open(APPEARANCE_SETTINGS_JSON_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            # Ensure all keys from default are present, if not, add them from default & re-save
            updated = False
            for key, value in DEFAULT_APPEARANCE_SETTINGS.items():
                if key not in settings:
                    settings[key] = value
                    updated = True
            if updated:
                _save_appearance_settings(settings) # Re-save with defaults for missing keys
            return settings
    except Exception as e:
        flash(f'Error loading appearance_settings.json: {e}. Using defaults and attempting to recreate.', 'warning')
        _save_appearance_settings(DEFAULT_APPEARANCE_SETTINGS.copy()) # Attempt to fix by recreating
        return DEFAULT_APPEARANCE_SETTINGS.copy()

def _save_appearance_settings(settings_dict):
    try:
        os.makedirs(os.path.dirname(APPEARANCE_SETTINGS_JSON_PATH), exist_ok=True)
        with open(APPEARANCE_SETTINGS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, indent=4)
        # Removed flash from here, will be handled by the route
        return True
    except Exception as e:
        flash(f'Error saving appearance_settings.json: {e}', 'danger')
        return False

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not ADMIN_USERNAME or not ADMIN_PASSWORD: # Check if credentials are set at all
            flash('Admin credentials are not configured on the server. Please set ADMIN_USERNAME and ADMIN_PASSWORD in .env.', 'danger')
        elif username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session.permanent = True
            flash('Login successful!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    if 'admin_logged_in' in session:
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/admin_login.html', title='Admin Login')

@admin_bp.route('/logout')
@login_required
def logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('admin/admin_dashboard.html', title='Admin Dashboard')

@admin_bp.route('/rules', methods=['GET', 'POST'])
@login_required
def manage_rules():
    _ensure_csv_file_and_headers()
    form_data_for_repopulation = {}
    edit_mode_rule_id = request.args.get('edit_rule_id', None)

    if request.method == 'POST':
        # action = request.form.get('submit_action') # From the submit button name
        # For add/update, the form fields are directly processed
        rule_id = request.form.get('rule_id', '').strip()
        context_required = request.form.get('context_required', '').strip().lower() or None
        pattern = request.form.get('pattern', '').strip().lower()
        response_text = request.form.get('response', '').strip()
        set_context_on_response = request.form.get('set_context_on_response', '').strip().lower() or None
        if set_context_on_response == 'clear': # Standardize value for clearing context
            set_context_on_response = 'clear'
        go_to_rule_id = request.form.get('go_to_rule_id', '').strip() or None

        form_data_for_repopulation = request.form

        if not rule_id:
            flash('Rule ID is required.', 'danger')
        elif not pattern and not response_text and not go_to_rule_id :
             flash('A rule must have at least a Pattern, or a Response, or a GoTo Rule ID.', 'warning')
        elif pattern == '*' and not context_required: # '*' pattern must have a context
             flash("Pattern '*' (match any input) requires a 'Context Required' to be set for specificity.", 'danger')
        else:
            all_rules = _read_rules_from_csv()
            new_rule_data = {
                'Rule_ID': rule_id, 'Context_Required': context_required,
                'Pattern': pattern, 'Response': response_text,
                'Set_Context_On_Response': set_context_on_response, 'GoTo_Rule_ID': go_to_rule_id
            }
            rule_found_for_update = False
            for i, r in enumerate(all_rules):
                if r.get('Rule_ID') == rule_id:
                    all_rules[i] = new_rule_data
                    rule_found_for_update = True
                    break
            if not rule_found_for_update:
                all_rules.append(new_rule_data)

            if _write_rules_to_csv(all_rules): # This already flashes success/error and reloads
                return redirect(url_for('admin.manage_rules'))
            # If write fails, we fall through to render template with form_data_for_repopulation

    current_rules = _read_rules_from_csv()
    if edit_rule_id_param and not request.form: # If it's a GET request for editing
        for r in current_rules: # current_rules might be empty if read failed
            if r.get('Rule_ID') == edit_rule_id_param:
                form_data_for_repopulation = r
                break
        if not form_data_for_repopulation:
             flash(f'Rule ID "{edit_rule_id_param}" not found for editing. You can add it as a new rule.', 'warning')

    return render_template('admin/admin_manage_rules.html',
                           title='Manage Rules' if not edit_rule_id_param else f'Edit Rule: {edit_rule_id_param}',
                           rules=current_rules,
                           form_data=form_data_for_repopulation,
                           edit_rule_id=edit_rule_id_param, # Pass this to conditionally highlight form or change title
                           RULES_CSV_FILE_PATH_DISPLAY=RULES_CSV_FILE_PATH) # For display in template

@admin_bp.route('/rules/delete/<rule_id>', methods=['POST'])
@login_required
def delete_rule(rule_id):
    all_rules = _read_rules_from_csv()
    rules_to_keep = [r for r in all_rules if r.get('Rule_ID') != rule_id]
    if len(rules_to_keep) < len(all_rules):
        _write_rules_to_csv(rules_to_keep) # This flashes success/error and reloads
    else:
        flash(f'Rule ID "{rule_id}" not found for deletion.', 'warning')
    return redirect(url_for('admin.manage_rules'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/rules/upload', methods=['POST'])
@login_required
def upload_rules_file():
    if 'rules_file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(url_for('admin.manage_rules'))
    file = request.files['rules_file']
    if file.filename == '':
        flash('No file selected for uploading.', 'warning')
        return redirect(url_for('admin.manage_rules'))
    if file and allowed_file(file.filename):
        try:
            import io
            # Ensure stream is read as text, common pitfall with FileStorage
            file.stream.seek(0) # Rewind stream just in case
            stream = io.TextIOWrapper(file.stream, encoding='utf-8')
            reader = csv.DictReader(stream)

            normalized_expected_headers = [h.strip().lower() for h in EXPECTED_CSV_HEADERS]
            normalized_reader_fieldnames = [h.strip().lower() for h in reader.fieldnames] if reader.fieldnames else []

            if not reader.fieldnames or normalized_reader_fieldnames != normalized_expected_headers:
                flash(f'Uploaded CSV has incorrect headers. Expected: {EXPECTED_CSV_HEADERS}. Found: {reader.fieldnames}. File not processed.', 'danger')
                return redirect(url_for('admin.manage_rules'))

            uploaded_rules = []
            line_count = 0
            for row in reader:
                line_count += 1
                if not row.get('Rule_ID'): # Rule_ID is mandatory
                    flash(f'Skipped row #{line_count} in uploaded file: missing Rule_ID.', 'warning')
                    continue
                # Basic sanitization/normalization
                rule = {
                    'Rule_ID': row.get('Rule_ID', '').strip(),
                    'Context_Required': (row.get('Context_Required') or '').strip().lower() or None,
                    'Pattern': (row.get('Pattern') or '').strip().lower(),
                    'Response': (row.get('Response') or '').strip(),
                    'Set_Context_On_Response': (row.get('Set_Context_On_Response') or '').strip().lower() or None,
                    'GoTo_Rule_ID': (row.get('GoTo_Rule_ID') or '').strip() or None
                }
                if rule['Set_Context_On_Response'] == '': # Explicit empty string from CSV should be None unless it means "clear"
                     rule['Set_Context_On_Response'] = None # Or 'clear' if that's the desired keyword
                if rule['Pattern'] == '*' and not rule['Context_Required']:
                    flash(f"Skipped row for Rule ID '{rule['Rule_ID']}': Pattern '*' requires a 'Context_Required'.", "warning")
                    continue
                uploaded_rules.append(rule)

            if not uploaded_rules and line_count > 0 :
                 flash('No valid rules (e.g. missing Rule_ID or other validation failed) found in the uploaded file, though rows were present.', 'danger')
            elif not uploaded_rules:
                 flash('Uploaded file was empty or contained no data rows.', 'warning')
            else: # We have some rules from the upload
                if _write_rules_to_csv(uploaded_rules): # This flashes success & reloads chatbot
                    flash(f'Successfully uploaded and replaced rules from {secure_filename(file.filename)}. {len(uploaded_rules)} rules loaded.', 'success') # _write adds its own flash
        except Exception as e:
            flash(f'Error processing uploaded file: {e}', 'danger')
    else:
        flash('Invalid file type. Only .csv files are allowed.', 'danger')
    return redirect(url_for('admin.manage_rules'))

@admin_bp.route('/appearance', methods=['GET', 'POST'])
@login_required
def manage_appearance():
    current_settings = _load_appearance_settings() # Load current or defaults
    if request.method == 'POST':
        new_settings = {} # Populate from form, ensuring all keys are covered
        for key in DEFAULT_APPEARANCE_SETTINGS.keys(): # Use default keys as the definitive list
            form_value = request.form.get(key)
            if form_value is not None:
                 # Basic validation: if a color field, ensure it's a plausible hex color, etc.
                 # For now, just stripping. Add more validation as needed.
                if "color" in key:
                    form_value = form_value.strip().lower()
                    if not (form_value.startswith('#') and (len(form_value) == 7 or len(form_value) == 4)):
                        flash(f"Invalid format for {key.replace('_', ' ').title()}: '{form_value}'. Must be a hex color (e.g., #RRGGBB or #RGB). Using default.", "warning")
                        form_value = current_settings.get(key, DEFAULT_APPEARANCE_SETTINGS[key]) # Revert to current or default on bad format
                elif "font_family" == key and request.form.get("font_family") == "CUSTOM":
                     form_value = request.form.get("font_family_custom", "").strip()
                     if not form_value: # If custom is selected but no value, revert to default or current
                         flash("Custom font family selected but no value provided. Reverting.", "warning")
                         form_value = current_settings.get(key, DEFAULT_APPEARANCE_SETTINGS[key])
                else:
                    form_value = form_value.strip()
                new_settings[key] = form_value
            else:
                # Should not happen if form is submitted correctly, but as a fallback:
                new_settings[key] = current_settings.get(key, DEFAULT_APPEARANCE_SETTINGS[key])

        if _save_appearance_settings(new_settings):
            flash('Appearance settings saved successfully!', 'success') # Moved flash here
            return redirect(url_for('admin.manage_appearance'))
        # If save failed, current_settings (pre-POST attempt) are used for rendering by falling through

    # For GET, or if POST save failed, current_settings are from _load_appearance_settings()
    return render_template('admin/admin_manage_appearance.html', title='Manage Appearance', current_settings=current_settings)
