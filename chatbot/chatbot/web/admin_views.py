import os
import functools
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv

# Load environment variables to get admin credentials
# This script is in /app/chatbot/chatbot/web/admin_views.py
# .env is in /app/.env (project root)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
dotenv_path = os.path.join(project_root, '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    # print(f"DEBUG (admin_views): .env loaded from {dotenv_path}")
else:
    if load_dotenv(): # Fallback (e.g. if CWD is project root)
        # print("DEBUG (admin_views): .env loaded via default dotenv search.")
        pass
    else:
        print("WARNING (admin_views): .env file not found. Admin credentials may be missing.")

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin') # Default if not set
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'password') # Default if not set
if ADMIN_USERNAME == 'admin' and ADMIN_PASSWORD == 'password':
    print("WARNING (admin_views): Using default admin credentials. Set ADMIN_USERNAME and ADMIN_PASSWORD in .env for security.")


# The template_folder is relative to the Blueprint's location (admin_views.py)
# However, Flask typically resolves 'templates/admin' from the app's main template folder (chatbot/web/templates)
# For clarity and explicit control, let's use an absolute path or ensure app structure.
# Given blueprint is in 'web', and templates are in 'web/templates/admin', this should work.
# The 'admin/' prefix in render_template calls refers to subdirectories within the app's main template folder.
admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='admin') # Flask will look for templates in web/admin/templates if this was the root
                                                                                    # Or web/templates/admin (if app's template_folder is 'templates')

def login_required(view):
    """View decorator that redirects anonymous users to the login page."""
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
    if 'admin_logged_in' in session: # If already logged in, redirect to dashboard
        return redirect(url_for('admin.dashboard'))
    # For render_template, Flask searches in app's template_folder + blueprint's template_folder_subpath
    # So, 'admin/admin_login.html' means it looks for <app_template_folder>/admin/admin_login.html
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

@admin_bp.route('/rules')
@login_required
def manage_rules():
    return render_template('admin/admin_manage_rules.html', title='Manage Rules')

@admin_bp.route('/appearance')
@login_required
def manage_appearance():
    return render_template('admin/admin_manage_appearance.html', title='Manage Appearance')
