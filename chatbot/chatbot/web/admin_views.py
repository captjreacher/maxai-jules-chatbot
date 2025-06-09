import os
import functools
import csv
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv

# Determine Project Root (common way)
# This file is in chatbot/chatbot/web/admin_views.py
# Project root is three levels up to get to /app
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DOTENV_PATH = os.path.join(PROJECT_ROOT_DIR, '.env')
# Path to the rules.csv file, relative to the project root /app
RULES_CSV_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, 'chatbot', 'chatbot', 'data', 'rules.csv')

if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
    # print(f"DEBUG (admin_views): .env loaded from {DOTENV_PATH}")
else:
    if not load_dotenv(): # Fallback to default dotenv search
        print("WARNING (admin_views): .env file not found. Admin auth and other .env dependent features may fail.")

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin') # Default if not set
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'password') # Default if not set
if ADMIN_USERNAME == 'admin' and ADMIN_PASSWORD == 'password' and not os.getenv('FLASK_ENV') == 'testing': # Avoid warning in tests
    print("WARNING (admin_views): Using default admin credentials. Set ADMIN_USERNAME and ADMIN_PASSWORD in .env for security.")

# The template_folder for a blueprint is relative to the blueprint's root path if specified.
# However, when using render_template('admin/template.html'), Flask's default loader
# (if app's template_folder is 'templates') will look for 'templates/admin/template.html'.
# Setting template_folder here to '../templates/admin' means from 'web/admin_views.py' -> 'web/' -> 'templates/' -> 'admin/'. This is correct.
admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='../templates/admin')

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin.login', next=request.url))
        return view(**kwargs)
    return wrapped_view

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
    return render_template('admin/admin_login.html', title='Admin Login') # Looks for <app_template_folder>/admin/admin_login.html

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
    rules_list = [] # Renamed to avoid conflict with 'rules' module if ever imported
    # Ensure rules.csv directory and file exists with headers
    try:
        os.makedirs(os.path.dirname(RULES_CSV_FILE_PATH), exist_ok=True)
        file_exists_before_open = os.path.exists(RULES_CSV_FILE_PATH)
        is_empty_or_new = not file_exists_before_open or os.path.getsize(RULES_CSV_FILE_PATH) == 0

        if is_empty_or_new:
            with open(RULES_CSV_FILE_PATH, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['pattern', 'response'])
            if not file_exists_before_open:
                 flash('rules.csv created with headers.', 'info')
            else:
                 flash('Added headers to empty rules.csv.', 'info')
        else: # File exists and is not empty, check headers
            with open(RULES_CSV_FILE_PATH, 'r+', newline='') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if not headers or [h.strip().lower() for h in headers] != ['pattern', 'response']:
                    flash('WARNING: rules.csv exists but has incorrect or missing headers (expected "pattern,response"). Manual check advised.', 'warning')
                    # Decide on recovery strategy: backup & recreate, or just warn. For now, warn.
    except Exception as e:
        flash(f'Error initializing rules.csv: {e}', 'danger')


    if request.method == 'POST':
        form_action = request.form.get('action', 'add_rule') # Differentiate if other actions come later

        if form_action == 'add_rule':
            pattern = request.form.get('pattern')
            response_text = request.form.get('response')
            if pattern and response_text:
                try:
                    with open(RULES_CSV_FILE_PATH, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([pattern, response_text])
                    flash('Rule added successfully!', 'success')
                    return redirect(url_for('admin.manage_rules'))
                except Exception as e:
                    flash(f'Error adding rule: {e}', 'danger')
            else:
                flash('Pattern and response cannot be empty for adding a rule.', 'warning')

    # For GET request, load and display rules
    try:
        with open(RULES_CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # DictReader uses first row as fieldnames by default.
            # Ensure fieldnames are what we expect if file could be malformed.
            if reader.fieldnames and [name.strip().lower() for name in reader.fieldnames] == ['pattern', 'response']:
                rules_list = list(reader)
            elif reader.fieldnames: # Headers are there but not what we expect
                flash(f"Warning: rules.csv headers are '{', '.join(reader.fieldnames)}', expected 'pattern, response'. Display may be incorrect.", "warning")
                # Attempt to read anyway if possible, or provide empty list
                # rules_list = list(reader) # This might map data incorrectly
            else: # No headers found by DictReader (e.g. empty file after header write failed, or truly no headers)
                if os.path.getsize(RULES_CSV_FILE_PATH) > 0 : # File has content but DictReader found no headers
                     flash('Warning: rules.csv seems to have no headers. Cannot display rules correctly.', 'warning')

    except FileNotFoundError:
        flash('rules.csv not found. It should have been created. Check permissions or logs.', 'danger')
    except Exception as e:
        flash(f'Error reading rules.csv: {e}', 'danger')

    return render_template('admin/admin_manage_rules.html', title='Manage Rules', rules=rules_list, RULES_CSV_FILE_PATH=RULES_CSV_FILE_PATH)

@admin_bp.route('/appearance')
@login_required
def manage_appearance():
    return render_template('admin/admin_manage_appearance.html', title='Manage Appearance')

# Placeholder for upload_rules_file, to be implemented in a later step
@admin_bp.route('/upload_rules', methods=['POST'])
@login_required
def upload_rules_file():
    flash('File upload functionality is not yet implemented.', 'info')
    return redirect(url_for('admin.manage_rules'))
