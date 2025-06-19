import os
import functools
import csv
import json
from dotenv import load_dotenv # ENSURED IMPORT IS HERE
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DOTENV_PATH = os.path.join(PROJECT_ROOT_DIR, '.env')
RULES_CSV_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'data', 'rules.csv')
APPEARANCE_SETTINGS_JSON_PATH = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'web', 'appearance_settings.json')
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'data', 'uploads')
ALLOWED_EXTENSIONS = {'csv'}
EXPECTED_CSV_HEADERS = ['Rule_ID', 'Context_Required', 'Pattern', 'Response', 'Set_Context_On_Response', 'GoTo_Rule_ID']

# Load .env file - This should be done once, ideally when the module is first loaded.
if os.path.exists(DOTENV_PATH):
    print(f"INFO (admin_views): Loading .env file from {DOTENV_PATH}")
    load_dotenv(dotenv_path=DOTENV_PATH) # Call the imported function
else:
    if load_dotenv(): # Try loading from CWD or other default dotenv search paths
        print("INFO (admin_views): .env file loaded via default dotenv search behavior.")
    else:
        print("WARNING (admin_views): .env file not found at project root or via default search. Admin auth and other .env dependent features may fail.")

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
# FLASK_SECRET_KEY is used by app.py directly

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='../templates/admin')

# Import chatbot instance and core class for reloading rules
from chatbot.chatbot.core.rules_based_chatbot import get_chatbot_instance

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'admin_logged_in' not in session:
            flash('Please log in to access the admin panel.', 'warning')
            return redirect(url_for('admin.login', next=request.url))
        return view(**kwargs)
    return wrapped_view

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

def _ensure_csv_file_and_headers():
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
    else:
        try:
            with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                normalized_headers = [h.strip().lower() for h in headers]
                normalized_expected = [h.strip().lower() for h in EXPECTED_CSV_HEADERS]
                if normalized_headers != normalized_expected:
                    print(f"WARNING (admin_views): rules.csv headers mismatch. Expected: {EXPECTED_CSV_HEADERS}, Found: {headers}")
                    flash(f'WARNING: rules.csv headers are incorrect. Expected {EXPECTED_CSV_HEADERS}. Found {headers}. Operations may fail.', 'warning')
                    return False
            return True
        except Exception as e:
            print(f"ERROR (admin_views): Error verifying CSV headers: {e}")
            flash(f'Error verifying rules.csv headers: {e}', 'danger')
            return False

def _read_rules_from_csv():
    rules = []
    if not os.path.exists(RULES_CSV_FILE_PATH):
        _ensure_csv_file_and_headers()
        if not os.path.exists(RULES_CSV_FILE_PATH): # Still doesn't exist after attempt
             flash('rules.csv does not exist and could not be created.', 'danger')
             return rules
    try:
        with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
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
        _ensure_csv_file_and_headers()
        with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=EXPECTED_CSV_HEADERS, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rules_list_of_dicts)

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

def _load_appearance_settings():
    if not os.path.exists(APPEARANCE_SETTINGS_JSON_PATH):
        print(f"INFO: {APPEARANCE_SETTINGS_JSON_PATH} not found. Creating with default settings.")
        _save_appearance_settings(DEFAULT_APPEARANCE_SETTINGS.copy())
        return DEFAULT_APPEARANCE_SETTINGS.copy()
    try:
        with open(APPEARANCE_SETTINGS_JSON_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            updated = False
            for key, value in DEFAULT_APPEARANCE_SETTINGS.items():
                if key not in settings:
                    settings[key] = value
                    updated = True
            if updated: # If new default keys were added
                _save_appearance_settings(settings)
            return settings
    except Exception as e:
        flash(f'Error loading appearance_settings.json: {e}. Using defaults and attempting to recreate.', 'warning')
        _save_appearance_settings(DEFAULT_APPEARANCE_SETTINGS.copy())
        return DEFAULT_APPEARANCE_SETTINGS.copy()

def _save_appearance_settings(settings_dict):
    try:
        os.makedirs(os.path.dirname(APPEARANCE_SETTINGS_JSON_PATH), exist_ok=True)
        with open(APPEARANCE_SETTINGS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, indent=4)
        # Flash moved to the route to give context
        return True
    except Exception as e:
        flash(f'Error saving appearance_settings.json: {e}', 'danger')
        return False

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not ADMIN_USERNAME or not ADMIN_PASSWORD:
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
    edit_rule_id_param = request.args.get('edit_rule_id', None)

    if request.method == 'POST':
        rule_id = request.form.get('rule_id', '').strip()
        context_required = request.form.get('context_required', '').strip().lower() or None
        pattern = request.form.get('pattern', '').strip().lower()
        response_text = request.form.get('response', '').strip()
        set_context_on_response = request.form.get('set_context_on_response', '').strip().lower() or None
        if set_context_on_response == 'clear':
            set_context_on_response = 'clear' # Ensure 'clear' is stored consistently
        go_to_rule_id = request.form.get('go_to_rule_id', '').strip() or None

        form_data_for_repopulation = request.form

        if not rule_id:
            flash('Rule ID is required.', 'danger')
        elif not pattern and not response_text and not go_to_rule_id :
             flash('A rule must have at least a Pattern, or a Response, or a GoTo Rule ID.', 'warning')
        elif pattern == '*' and not context_required:
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

            if _write_rules_to_csv(all_rules):
                return redirect(url_for('admin.manage_rules'))

    current_rules = _read_rules_from_csv()
    if edit_rule_id_param and not request.form:
        for r in current_rules:
            if r.get('Rule_ID') == edit_rule_id_param:
                form_data_for_repopulation = r
                break
        if not form_data_for_repopulation:
             flash(f'Rule ID "{edit_rule_id_param}" not found for editing. You can add it as a new rule.', 'warning')

    return render_template('admin/admin_manage_rules.html',
                           title='Manage Rules' if not edit_rule_id_param else f'Edit Rule: {edit_rule_id_param}',
                           rules=current_rules,
                           form_data=form_data_for_repopulation,
                           edit_rule_id=edit_rule_id_param,
                           RULES_CSV_FILE_PATH_DISPLAY=RULES_CSV_FILE_PATH)

@admin_bp.route('/rules/delete/<rule_id>', methods=['POST'])
@login_required
def delete_rule(rule_id):
    all_rules = _read_rules_from_csv()
    rules_to_keep = [r for r in all_rules if r.get('Rule_ID') != rule_id]
    if len(rules_to_keep) < len(all_rules):
        _write_rules_to_csv(rules_to_keep)
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
            file.stream.seek(0)
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
                if not row.get('Rule_ID'):
                    flash(f'Skipped row #{line_count} in uploaded file: missing Rule_ID.', 'warning')
                    continue
                rule = {
                    'Rule_ID': row.get('Rule_ID', '').strip(),
                    'Context_Required': (row.get('Context_Required') or '').strip().lower() or None,
                    'Pattern': (row.get('Pattern') or '').strip().lower(),
                    'Response': (row.get('Response') or '').strip(),
                    'Set_Context_On_Response': (row.get('Set_Context_On_Response') or '').strip().lower() or None,
                    'GoTo_Rule_ID': (row.get('GoTo_Rule_ID') or '').strip() or None
                }
                if rule['Set_Context_On_Response'] == '':
                     rule['Set_Context_On_Response'] = None
                if rule['Pattern'] == '*' and not rule['Context_Required']:
                    flash(f"Skipped row for Rule ID '{rule['Rule_ID']}': Pattern '*' requires a 'Context_Required'.", "warning")
                    continue
                uploaded_rules.append(rule)

            if not uploaded_rules and line_count > 0 :
                 flash('No valid rules (e.g. missing Rule_ID or other validation failed) found in the uploaded file, though rows were present.', 'danger')
            elif not uploaded_rules:
                 flash('Uploaded file was empty or contained no data rows.', 'warning')
            else:
                if _write_rules_to_csv(uploaded_rules):
                    flash(f'Successfully uploaded and replaced rules from {secure_filename(file.filename)}. {len(uploaded_rules)} rules loaded.', 'success')
        except Exception as e:
            flash(f'Error processing uploaded file: {e}', 'danger')
    else:
        flash('Invalid file type. Only .csv files are allowed.', 'danger')
    return redirect(url_for('admin.manage_rules'))

@admin_bp.route('/appearance', methods=['GET', 'POST'])
@login_required
def manage_appearance():
    current_settings = _load_appearance_settings()
    if request.method == 'POST':
        new_settings = {}
        for key in DEFAULT_APPEARANCE_SETTINGS.keys():
            form_value = request.form.get(key)
            if form_value is not None:
                form_value = form_value.strip()
                if "color" in key:
                    if not (form_value.startswith('#') and len(form_value) in [4, 7]) and not form_value.isalpha(): # Simple check for hex or name
                        flash(f"Invalid format for {key.replace('_', ' ').title()}: '{form_value}'. Must be valid hex color or CSS color name.", 'warning')
                        form_value = current_settings.get(key, DEFAULT_APPEARANCE_SETTINGS[key])
                elif "font_family" == key and request.form.get("font_family") == "CUSTOM":
                     custom_font = request.form.get("font_family_custom", "").strip()
                     if not custom_font:
                         flash("Custom font family selected but no value provided. Reverting to previous or default.", "warning")
                         form_value = current_settings.get(key, DEFAULT_APPEARANCE_SETTINGS[key])
                     else:
                         form_value = custom_font
                new_settings[key] = form_value
            else:
                new_settings[key] = current_settings.get(key, DEFAULT_APPEARANCE_SETTINGS[key])

        if _save_appearance_settings(new_settings):
            flash('Appearance settings saved successfully!', 'success') # Flash moved from _save to here
            return redirect(url_for('admin.manage_appearance'))
        # If save failed, current_settings are re-passed to template

    return render_template('admin/admin_manage_appearance.html', title='Manage Appearance', current_settings=current_settings)
