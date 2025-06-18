import os
import functools
import csv
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename # For file uploads later
from dotenv import load_dotenv

PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DOTENV_PATH = os.path.join(PROJECT_ROOT_DIR, '.env')
RULES_CSV_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'data', 'rules.csv')
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'data', 'uploads')
ALLOWED_EXTENSIONS = {'csv'}

EXPECTED_CSV_HEADERS = ['Rule_ID', 'Context_Required', 'Pattern', 'Response', 'Set_Context_On_Response', 'GoTo_Rule_ID']

if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    if not load_dotenv():
        print("WARNING (admin_views): .env file not found. Admin auth may fail.")

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='../templates/admin')

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
    if not os.path.exists(RULES_CSV_FILE_PATH) or os.path.getsize(RULES_CSV_FILE_PATH) == 0:
        try:
            os.makedirs(os.path.dirname(RULES_CSV_FILE_PATH), exist_ok=True)
            with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(EXPECTED_CSV_HEADERS)
            # flash('rules.csv created with headers.', 'info') # Flashing here might be too early if app context not avail
            print("INFO (admin_views): rules.csv created/headers written by _ensure_csv_file_and_headers")
            return True
        except Exception as e:
            print(f'ERROR (admin_views): Error creating rules.csv: {e}')
            # flash(f'Error creating rules.csv: {e}', 'danger')
            return False
    else:
        try:
            with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, []) 
                if [h.strip() for h in headers] != EXPECTED_CSV_HEADERS:
                    # flash(f'rules.csv has incorrect headers. Expected: {EXPECTED_CSV_HEADERS}. Found: {headers}.', 'danger')
                    print(f"WARNING (admin_views): rules.csv headers mismatch. Expected: {EXPECTED_CSV_HEADERS}, Found: {headers}")
                    return False 
            return True 
        except Exception as e:
            # flash(f'Error verifying rules.csv headers: {e}', 'danger')
            print(f"ERROR (admin_views): Error verifying CSV headers: {e}")
            return False

def _read_rules_from_csv():
    rules = []
    if not _ensure_csv_file_and_headers():
        flash('rules.csv has header issues or could not be created. Please check file or server logs.', 'danger')
        return rules
    try:
        with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or not all(h in reader.fieldnames for h in EXPECTED_CSV_HEADERS):
                 flash('CSV headers are missing or incorrect. Cannot read rules reliably.','danger')
                 return []
            rules = list(reader)
    except Exception as e:
        flash(f'Error reading rules from rules.csv: {e}', 'danger')
    return rules

def _write_rules_to_csv(rules_list_of_dicts):
    try:
        # _ensure_csv_file_and_headers() # Not needed here, assume file exists if we are writing to it after read
        os.makedirs(os.path.dirname(RULES_CSV_FILE_PATH), exist_ok=True) # Ensure dir exists
        with open(RULES_CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=EXPECTED_CSV_HEADERS, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rules_list_of_dicts)
        get_chatbot_instance()._load_rules_from_csv() # Force reload
        flash('Rules saved and chatbot reloaded.', 'success')
        return True
    except Exception as e:
        flash(f'Error writing rules to rules.csv: {e}', 'danger')
        return False

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not ADMIN_USERNAME or not ADMIN_PASSWORD:
            flash('Admin credentials are not configured on the server.', 'danger')
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
    form_data_for_repopulation = {} 
    edit_mode = False

    if request.method == 'POST':
        rule_id = request.form.get('rule_id', '').strip()
        context_required = request.form.get('context_required', '').strip().lower()
        pattern = request.form.get('pattern', '').strip().lower()
        response_text = request.form.get('response', '').strip()
        set_context_on_response = request.form.get('set_context_on_response', '').strip().lower()
        go_to_rule_id = request.form.get('go_to_rule_id', '').strip()

        form_data_for_repopulation = request.form 

        if not rule_id:
            flash('Rule ID is required.', 'danger')
        elif not pattern and not go_to_rule_id and not response_text: # Rule must have a pattern or a goto or a response
             flash('A rule must have at least a Pattern, or a Response, or a GoTo Rule ID.', 'warning')
        else:
            all_rules = _read_rules_from_csv()
            new_rule_data = {
                'Rule_ID': rule_id,
                'Context_Required': context_required,
                'Pattern': pattern,
                'Response': response_text,
                'Set_Context_On_Response': set_context_on_response,
                'GoTo_Rule_ID': go_to_rule_id
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
    edit_rule_id_param = request.args.get('edit_rule_id')
    if edit_rule_id_param and not request.form: 
        for r in current_rules:
            if r.get('Rule_ID') == edit_rule_id_param:
                form_data_for_repopulation = r 
                edit_mode = True
                break
                
    return render_template('admin/admin_manage_rules.html', 
                           title='Manage Rules' if not edit_mode else f'Edit Rule {edit_rule_id_param}', 
                           rules=current_rules, 
                           form_data=form_data_for_repopulation,
                           edit_mode=edit_mode,
                           RULES_CSV_FILE_PATH_DISPLAY=RULES_CSV_FILE_PATH)

@admin_bp.route('/rules/delete/<rule_id>', methods=['POST'])
@login_required
def delete_rule(rule_id):
    all_rules = _read_rules_from_csv()
    rules_to_keep = [r for r in all_rules if r.get('Rule_ID') != rule_id]
    
    if len(rules_to_keep) < len(all_rules):
        if _write_rules_to_csv(rules_to_keep):
            flash(f'Rule ID "{rule_id}" deleted successfully.', 'success')
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
            stream = io.TextIOWrapper(file.stream, encoding='utf-8')
            reader = csv.DictReader(stream)
            
            if not reader.fieldnames or [h.strip() for h in reader.fieldnames] != EXPECTED_CSV_HEADERS:
                flash(f'Uploaded CSV has incorrect headers. Expected: {EXPECTED_CSV_HEADERS}. Found: {reader.fieldnames}. File not processed.', 'danger')
                return redirect(url_for('admin.manage_rules'))

            uploaded_rules = []
            line_count = 0
            for row in reader:
                line_count += 1
                if not row.get('Rule_ID'): # Rule_ID is essential
                    flash(f'Skipped row #{line_count} in uploaded file: missing Rule_ID.', 'warning')
                    continue
                rule = {
                    'Rule_ID': row.get('Rule_ID', '').strip(),
                    'Context_Required': row.get('Context_Required', '').strip().lower(),
                    'Pattern': row.get('Pattern', '').strip().lower(),
                    'Response': row.get('Response', '').strip(),
                    'Set_Context_On_Response': row.get('Set_Context_On_Response', '').strip().lower(),
                    'GoTo_Rule_ID': row.get('GoTo_Rule_ID', '').strip()
                }
                uploaded_rules.append(rule)
            
            if not uploaded_rules and line_count > 0 :
                 flash('No valid rules found in the uploaded file (e.g., all rows missing Rule_ID).', 'danger')
            elif not uploaded_rules:
                 flash('Uploaded file was empty or contained no valid data rows.', 'warning')
            else:
                if _write_rules_to_csv(uploaded_rules):
                    flash(f'Successfully uploaded and replaced rules from {secure_filename(file.filename)}. {len(uploaded_rules)} rules loaded.', 'success')
        except Exception as e:
            flash(f'Error processing uploaded file: {e}', 'danger')
    else:
        flash('Invalid file type. Only .csv files are allowed.', 'danger')
        
    return redirect(url_for('admin.manage_rules'))

@admin_bp.route('/appearance') 
@login_required
def manage_appearance():
    return render_template('admin/admin_manage_appearance.html', title='Manage Appearance')
