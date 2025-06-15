import os
import functools
import csv
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename # For file uploads later
from dotenv import load_dotenv

# Assuming this file (admin_views.py) is in /app/chatbot/chatbot/web/
# Project root is three levels up (/app)
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DOTENV_PATH = os.path.join(PROJECT_ROOT_DIR, '.env')
RULES_CSV_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'data', 'rules.csv')
EXPECTED_CSV_HEADERS = ['Rule_ID', 'Context_Required', 'Pattern', 'Response', 'Set_Context_On_Response', 'GoTo_Rule_ID']

if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    if not load_dotenv(): # Try default search paths
        print("WARNING (admin_views): .env file not found. Admin auth and other .env dependent features may fail.")

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin') # Default if not set
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'password') # Default if not set
# FLASK_SECRET_KEY is used by app.py, not directly here.
if ADMIN_USERNAME == 'admin' and ADMIN_PASSWORD == 'password' and not os.getenv('FLASK_ENV') == 'testing':
    print("WARNING (admin_views): Using default admin credentials. Set ADMIN_USERNAME and ADMIN_PASSWORD in .env for security.")

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='../templates/admin')

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin.login', next=request.url))
        return view(**kwargs)
    return wrapped_view

# --- Utility functions for CSV handling ---
def _read_rules_from_csv():
    rules = []
    if not os.path.exists(RULES_CSV_FILE_PATH):
        # flash('rules.csv does not exist yet. It will be created when you add the first rule.', 'info')
        return rules
    try:
        with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Normalize expected headers for comparison
            normalized_expected_headers = [h.strip().lower() for h in EXPECTED_CSV_HEADERS]
            # Normalize actual headers from file for comparison
            normalized_reader_fieldnames = [h.strip().lower() for h in reader.fieldnames] if reader.fieldnames else []

            if not reader.fieldnames or normalized_reader_fieldnames != normalized_expected_headers:
                flash(f'WARNING: rules.csv headers are {reader.fieldnames if reader.fieldnames else "MISSING"}, expected {EXPECTED_CSV_HEADERS}. Rules may not load or display correctly.', 'warning')
                if not reader.fieldnames or not all(h_expected.lower() in normalized_reader_fieldnames for h_expected in normalized_expected_headers):
                     return [] # Critical headers missing, cannot reliably process
            rules = list(reader)
    except Exception as e:
        flash(f'Error reading rules.csv: {e}', 'danger')
    return rules

def _write_rules_to_csv(rules_list_of_dicts):
    try:
        os.makedirs(os.path.dirname(RULES_CSV_FILE_PATH), exist_ok=True)
        with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=EXPECTED_CSV_HEADERS)
            writer.writeheader()
            writer.writerows(rules_list_of_dicts)
        return True
    except Exception as e:
        flash(f'Error writing to rules.csv: {e}', 'danger')
        return False

def _ensure_csv_headers_exist():
    if not os.path.exists(RULES_CSV_FILE_PATH) or os.path.getsize(RULES_CSV_FILE_PATH) == 0:
        print(f"INFO (_ensure_csv_headers_exist): Creating {RULES_CSV_FILE_PATH} with headers.")
        _write_rules_to_csv([]) # Create empty file with headers
        flash('rules.csv created with necessary headers.', 'info')
    else: # File exists, check headers
        try:
            with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                normalized_headers = [h.strip().lower() for h in headers] if headers else []
                normalized_expected_headers = [eh.strip().lower() for eh in EXPECTED_CSV_HEADERS]
                if not headers or normalized_headers != normalized_expected_headers:
                     flash(f'WARNING: rules.csv headers are {headers}, expected {EXPECTED_CSV_HEADERS}. Operations might fail or behave unexpectedly.', 'warning')
        except Exception as e:
            flash(f'Error verifying headers of existing rules.csv: {e}', 'danger')


# --- Routes ---
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
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
    _ensure_csv_headers_exist()
    form_data_for_repopulation = {}
    edit_mode = request.args.get('edit_rule_id', None) # Check if we are in edit mode from GET param

    if request.method == 'POST':
        action = request.form.get('submit_action', 'Add/Update Rule') # From the submit button's name/value

        if action == 'Add/Update Rule':
            rule_id = request.form.get('rule_id', '').strip()
            context_required = request.form.get('context_required', '').strip() or None # Store empty as None
            pattern = request.form.get('pattern', '').strip()
            response_text = request.form.get('response', '').strip()
            set_context_on_response = request.form.get('set_context_on_response', '').strip().lower() or None
            if set_context_on_response == 'clear': # Standardize 'clear'
                set_context_on_response = 'clear'
            go_to_rule_id = request.form.get('go_to_rule_id', '').strip() or None

            form_data_for_repopulation = request.form

            if not rule_id or not pattern :
                flash('Rule ID and Pattern are required.', 'danger')
            elif pattern == '*' and not context_required:
                flash("Pattern '*' (match any input) requires a 'Context Required' to be set for specificity.", 'danger')
            else:
                rules = _read_rules_from_csv()
                new_rule_data = {
                    'Rule_ID': rule_id,
                    'Context_Required': context_required,
                    'Pattern': pattern,
                    'Response': response_text,
                    'Set_Context_On_Response': set_context_on_response,
                    'GoTo_Rule_ID': go_to_rule_id
                }

                rule_exists_at_index = -1
                for i, rule in enumerate(rules):
                    if rule.get('Rule_ID') == rule_id:
                        rule_exists_at_index = i
                        break

                if rule_exists_at_index != -1:
                    rules[rule_exists_at_index] = new_rule_data
                    flash_msg = f'Rule "{rule_id}" updated successfully!'
                else:
                    rules.append(new_rule_data)
                    flash_msg = f'Rule "{rule_id}" added successfully!'

                if _write_rules_to_csv(rules):
                    flash(flash_msg, 'success')
                    from chatbot.chatbot.core.rules_based_chatbot import get_chatbot_instance
                    chatbot_instance = get_chatbot_instance()
                    if chatbot_instance: # Ensure instance exists
                         chatbot_instance._load_rules_from_csv() # Force reload
                         flash('Chatbot rules reloaded.', 'info')
                    return redirect(url_for('admin.manage_rules'))
                else:
                    # Error writing, form_data_for_repopulation already set
                    pass # Flash message for write error is in _write_rules_to_csv

    if edit_mode: # Populating form for editing from a GET request
        all_rules_for_edit_lookup = _read_rules_from_csv()
        rule_to_edit = next((rule for rule in all_rules_for_edit_lookup if rule.get('Rule_ID') == edit_mode), None)
        if rule_to_edit:
            form_data_for_repopulation = rule_to_edit
        else:
            flash(f'Rule ID "{edit_mode}" not found for editing.', 'warning')
            # No redirect, just won't populate form, or user can ignore and add new.

    current_rules = _read_rules_from_csv()
    return render_template('admin/admin_manage_rules.html', title='Manage Chatbot Rules', rules=current_rules, form_data=form_data_for_repopulation, edit_rule_id=edit_mode, RULES_CSV_FILE_PATH=RULES_CSV_FILE_PATH)

@admin_bp.route('/rules/delete/<rule_id>', methods=['POST'])
@login_required
def delete_rule(rule_id):
    rules = _read_rules_from_csv()
    rule_found = False
    updated_rules = []
    for rule in rules:
        if rule.get('Rule_ID') == rule_id:
            rule_found = True
        else:
            updated_rules.append(rule)

    if rule_found:
        if _write_rules_to_csv(updated_rules):
            flash(f'Rule "{rule_id}" deleted successfully.', 'success')
            from chatbot.chatbot.core.rules_based_chatbot import get_chatbot_instance
            chatbot_instance = get_chatbot_instance()
            if chatbot_instance:
                chatbot_instance._load_rules_from_csv()
                flash('Chatbot rules reloaded.', 'info')
        else:
            flash(f'Failed to delete rule "{rule_id}" from CSV.', 'danger')
    else:
        flash(f'Rule "{rule_id}" not found for deletion.', 'warning')
    return redirect(url_for('admin.manage_rules'))

@admin_bp.route('/appearance')
@login_required
def manage_appearance():
    return render_template('admin/admin_manage_appearance.html', title='Manage Appearance')

@admin_bp.route('/rules/upload', methods=['POST'])
@login_required
def upload_rules_file():
    if 'rules_file' not in request.files:
        flash('No file part in the request.', 'warning')
        return redirect(url_for('admin.manage_rules'))

    file = request.files['rules_file']
    if file.filename == '':
        flash('No selected file.', 'warning')
        return redirect(url_for('admin.manage_rules'))

    if file and file.filename.endswith('.csv'):
        try:
            # Read the uploaded CSV file content
            # Werkzeug FileStorage is a stream. Read it as text.
            stream = file.stream.read().decode("utf-8")
            # Use io.StringIO to treat the string as a file for csv.DictReader
            import io
            string_io_file = io.StringIO(stream)

            reader = csv.DictReader(string_io_file)

            # Validate headers of the uploaded file
            uploaded_fieldnames = reader.fieldnames if reader.fieldnames else []
            normalized_uploaded_fieldnames = [h.strip().lower() for h in uploaded_fieldnames]
            normalized_expected_headers = [h.strip().lower() for h in EXPECTED_CSV_HEADERS]

            if not uploaded_fieldnames or normalized_uploaded_fieldnames != normalized_expected_headers:
                flash(f'Uploaded CSV has incorrect headers. Expected: {EXPECTED_CSV_HEADERS}, Found: {uploaded_fieldnames}. Rules not replaced.', 'danger')
                return redirect(url_for('admin.manage_rules'))

            # If headers are correct, proceed to parse and write
            rules_from_upload = []
            for row in reader:
                # Basic validation for each row from upload
                if row.get('Rule_ID') and row.get('Pattern'):
                    rule_data = {header: row.get(header, '').strip() for header in EXPECTED_CSV_HEADERS}
                    # Normalize specific fields if needed (e.g. context to lower or None)
                    rule_data['Context_Required'] = rule_data.get('Context_Required','').lower() or None
                    rule_data['Set_Context_On_Response'] = rule_data.get('Set_Context_On_Response','').lower() or None
                    if rule_data['Set_Context_On_Response'] == '': # Ensure empty string results in None for consistency if desired, or handle as 'clear'
                        rule_data['Set_Context_On_Response'] = None
                    rule_data['GoTo_Rule_ID'] = rule_data.get('GoTo_Rule_ID','') or None
                    rules_from_upload.append(rule_data)
                else:
                    flash(f"Skipped a row during upload due to missing Rule_ID or Pattern: {row}", "warning")

            if _write_rules_to_csv(rules_from_upload):
                flash(f'Successfully uploaded and replaced rules from {secure_filename(file.filename)}.', 'success')
                from chatbot.chatbot.core.rules_based_chatbot import get_chatbot_instance
                chatbot_instance = get_chatbot_instance()
                if chatbot_instance:
                    chatbot_instance._load_rules_from_csv()
                    flash('Chatbot rules reloaded.', 'info')
            else:
                flash('Failed to write uploaded rules to CSV.', 'danger')

        except Exception as e:
            flash(f'Error processing uploaded CSV file: {e}', 'danger')
    else:
        flash('Invalid file type. Please upload a .csv file.', 'warning')

    return redirect(url_for('admin.manage_rules'))
