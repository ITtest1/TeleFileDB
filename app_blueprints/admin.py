from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, jsonify, current_app
import database
import bot_handler
import os
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__, template_folder='templates')

@admin_bp.route('/settings')
def settings():
    if 'user_id' not in session or database.get_user_by_id(session['user_id']).username != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('views.index'))

    current_cache_size_bytes = bot_handler.get_current_cache_size_bytes()
    current_cache_size_formatted = format_size(current_cache_size_bytes)
    
    users = database.get_all_users()

    return render_template('settings.html', current_cache_size=current_cache_size_formatted, users=users)

@admin_bp.route('/export_db', methods=['POST'])
def export_db():
    try:
        db_path = os.path.join(current_app.instance_path, 'files.db')
        return send_file(db_path, as_attachment=True, download_name='files.db')
    except Exception as e:
        flash(f'Error exporting database: {e}')
        return redirect(url_for('admin.settings'))

@admin_bp.route('/import_db', methods=['POST'])
def import_db():
    if 'db_file' not in request.files:
        flash('No file part')
        return redirect(url_for('admin.settings'))
    db_file = request.files['db_file']
    if db_file.filename == '':
        flash('No selected file')
        return redirect(url_for('admin.settings'))
    if db_file and secure_filename(db_file.filename) == 'files.db':
        try:
            db_file.save(os.path.join(current_app.instance_path, 'files.db'))
            flash('Database imported successfully. Restart application for changes to take effect.')
        except Exception as e:
            flash(f'Error importing database: {e}')
        return redirect(url_for('admin.settings'))
    else:
        flash('Invalid file. Please upload a file named files.db')
        return redirect(url_for('admin.settings'))



@admin_bp.route('/update_settings', methods=['POST'])
def update_settings():
    if 'user_id' not in session:
        flash('Unauthorized access.')
        return redirect(url_for('auth.login'))
    try:
        env_vars = {}
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key] = value

        
        env_vars['CACHE_MAX_SIZE_GB'] = request.form.get('CACHE_MAX_SIZE_GB')
        env_vars['CACHE_MAX_AGE_MINUTES'] = request.form.get('CACHE_MAX_AGE_MINUTES')
        env_vars['THUMBNAIL_WIDTH'] = request.form.get('THUMBNAIL_WIDTH')
        env_vars['THUMBNAIL_HEIGHT'] = request.form.get('THUMBNAIL_HEIGHT')

        with open('.env', 'w') as f:
            for key, value in env_vars.items():
                f.write(f'{key}={value}\n')

        flash('Settings updated successfully. Restart application for changes to take effect.')
    except Exception as e:
        flash(f'Error updating settings: {e}')
    return redirect(url_for('admin.settings'))

@admin_bp.route('/restart_app', methods=['POST'])
def restart_app():
    flash('Application is restarting...')
    os._exit(0)

@admin_bp.route('/admin/users')
def manage_users():
    if 'user_id' not in session or database.get_user_by_id(session['user_id']).username != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('views.index'))
    users = database.get_all_users()
    return render_template('manage_users.html', users=users)

@admin_bp.route('/admin/users/add', methods=['GET', 'POST'])
def add_user():
    if 'user_id' not in session or database.get_user_by_id(session['user_id']).username != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('views.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        paths = request.form.get('paths').splitlines()
        user = database.add_user(username, password)
        if user:
            database.update_user_paths(user.id, paths)
            flash('User added successfully!')
            return redirect(url_for('admin.manage_users'))
        else:
            flash('Username already exists.')
    return render_template('edit_user.html', user=None, paths="")

@admin_bp.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_id' not in session or database.get_user_by_id(session['user_id']).username != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('views.index'))
    user_to_edit = database.get_user_by_id(user_id)
    if not user_to_edit:
        flash('User not found.')
        return redirect(url_for('admin.manage_users'))
    if request.method == 'POST':
        password = request.form.get('password')
        paths = request.form.get('paths').splitlines()
        if password:
            user_to_edit.password = password # Note: use a password hashing library
        database.update_user_paths(user_id, paths)
        flash('User updated successfully!')
        return redirect(url_for('admin.manage_users'))
    paths = '\n'.join(database.get_user_paths(user_id))
    return render_template('edit_user.html', user=user_to_edit, paths=paths)

@admin_bp.route('/admin/users/delete/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or database.get_user_by_id(session['user_id']).username != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('views.index'))
    database.delete_user(user_id)
    flash('User deleted successfully!')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/clear_database', methods=['POST'])
def clear_database_route():
    if 'user_id' not in session:
        flash('Unauthorized access.')
        return redirect(url_for('auth.login'))
    try:
        database.clear_database()
        flash('Database cleared successfully.')
    except Exception as e:
        flash(f'Error clearing database: {e}')
    return redirect(url_for('admin.settings'))

@admin_bp.route('/clear_cache', methods=['POST'])
def clear_cache_route():
    if 'user_id' not in session:
        flash('Unauthorized access.')
        return redirect(url_for('auth.login'))
    try:
        bot_handler.clear_cache_manual()
        flash('Cache cleared successfully.')
    except Exception as e:
        flash(f'Error clearing cache: {e}')
    return redirect(url_for('admin.settings'))

@admin_bp.route('/clear_file_cache', methods=['POST'])
def clear_file_cache_route():
    current_app.logger.debug(f"Received clear cache request. Request data: {request.data}")
    current_app.logger.debug(f"Request Content-Type: {request.headers.get('Content-Type')}")
    try:
        data = request.get_json()
        current_app.logger.debug(f"Parsed JSON data: {data}")
        file_id = data.get('file_id')
        thumbnail_id = data.get('thumbnail_id')
        current_app.logger.debug(f"Extracted file_id: {file_id}, thumbnail_id: {thumbnail_id}")
    except Exception as e:
        current_app.logger.error(f"Error parsing JSON data: {e}")
        return jsonify({'success': False, 'message': 'Invalid JSON data'})
    if not file_id:
        current_app.logger.warning("File ID missing in clear cache request.")
        return jsonify({'success': False, 'message': 'File ID missing'})
    try:
        bot_handler.clear_file_cache(file_id, thumbnail_id)
        return jsonify({'success': True, 'message': 'Cache cleared'})
    except Exception as e:
        current_app.logger.error(f"Error clearing file cache for {file_id}: {e}")
        return jsonify({'success': False, 'message': str(e)})

# Need to import format_size or define it here
import math
def format_size(size_bytes):
    if size_bytes is None or size_bytes == 0:
        return "0 B"
    try:
        size_bytes = int(size_bytes)
    except (ValueError, TypeError):
        return "N/A"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

@admin_bp.route('/admin/clear_items_cache', methods=['POST'])
def clear_items_cache():
    if 'user_id' not in session or database.get_user_by_id(session['user_id']).username != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})

    data = request.get_json()
    items = data.get('items')

    if not items:
        return jsonify({'success': False, 'message': 'No items selected'})

    cleared_files = 0
    try:
        for item_data in items:
            item_id = item_data.get('id')
            item_type = item_data.get('type')

            if item_type == 'file':
                file = database.get_file_by_id(item_id)
                if file:
                    bot_handler.clear_file_cache(file.file_id, file.thumbnail_file_id)
                    cleared_files += 1
            elif item_type == 'folder':
                folder = database.get_file_by_id(item_id)
                if folder and folder.filename == '.folder_marker':
                    folder_path = folder.folder
                    files_in_folder = database.get_all_files_in_folder(folder_path)
                    for file in files_in_folder:
                        if file.filename != '.folder_marker':
                            bot_handler.clear_file_cache(file.file_id, file.thumbnail_file_id)
                            cleared_files += 1

        return jsonify({'success': True, 'message': f'Cleared cache for {cleared_files} files.'})
    except Exception as e:
        current_app.logger.error(f"Error clearing items cache: {e}")
        return jsonify({'success': False, 'message': str(e)})
