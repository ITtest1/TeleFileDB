from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import database

auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = database.get_user_by_username(username)
        if user and user.password == password: # Note: use a password hashing library like Werkzeug in a real app
            session['user_id'] = user.id
            flash('Logged in successfully!')
            return redirect(url_for('views.index'))
        else:
            flash('Invalid credentials.')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!')
    return redirect(url_for('auth.login'))

@auth_bp.before_app_request
def before_request():
    allowed_endpoints = ['auth.login', 'static', 'views.download_file', 'views.download_file_direct', 'views.stream_file_for_preview', 'views.get_thumbnail']
    if 'user_id' not in session and request.endpoint not in allowed_endpoints:
        return redirect(url_for('auth.login'))
