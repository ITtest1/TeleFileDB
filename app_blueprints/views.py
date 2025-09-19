from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, send_file, jsonify
import database
import os
import math
import json
from datetime import datetime
import bot_handler

views_bp = Blueprint('views', __name__, template_folder='templates')

@views_bp.route('/')
@views_bp.route('/index')
def index():
    view_mode = request.args.get('view_mode', 'list')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page_str = request.args.get('per_page', '20')
    per_page = int(per_page_str) if per_page_str != 'all' else None

    all_files = database.get_all_files_for_user(session['user_id'], sort_by, sort_order)

    all_items = []
    for item in all_files:
        all_items.append({'type': 'file', 'obj': item, 'name': item.filename, 'size': item.size, 'date': item.upload_date, 'folder': item.folder, 'mime_type': item.mime_type})

    if per_page is not None:
        total_items = len(all_items)
        total_pages = int(math.ceil(total_items / per_page))
        start = (page - 1) * per_page
        end = start + per_page
        paginated_items = all_items[start:end]
    else:
        total_pages = 1
        paginated_items = all_items

    return render_template('index.html', 
                           items=paginated_items, 
                           view_mode=view_mode, 
                           sort_by=sort_by, 
                           sort_order=sort_order, 
                           page=page, 
                           per_page=per_page_str, 
                           total_pages=total_pages, 
                           pagination_endpoint='views.index')

@views_bp.route('/folders', strict_slashes=False)
@views_bp.route('/folders/<int:folder_id>')
def folders(folder_id=None):
    view_mode = request.args.get('view_mode', 'list')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    page = request.args.get('page', 1, type=int)
    per_page_str = request.args.get('per_page', '20')
    per_page = int(per_page_str) if per_page_str != 'all' else None

    if folder_id is None:
        current_folder_path = 'root'
    else:
        folder = database.get_file_by_id(folder_id)
        if folder and folder.filename == '.folder_marker':
            current_folder_path = folder.folder
        else:
            flash('Invalid folder ID or not a folder.')
            return redirect(url_for('views.folders'))

    files, subfolders = database.get_folder_contents_for_user(session['user_id'], current_folder_path)
    if files is None and subfolders is None:
        flash('You do not have permission to access this folder.')
        return redirect(url_for('views.folders'))

    all_items = []
    for item in subfolders:
        all_items.append({'type': 'folder', 'obj': item, 'name': os.path.basename(item.folder), 'size': 0, 'date': item.upload_date, 'folder': item.folder, 'mime_type': 'folder'})
    for item in files:
        all_items.append({'type': 'file', 'obj': item, 'name': item.filename, 'size': item.size, 'date': item.upload_date, 'folder': item.folder, 'mime_type': item.mime_type})

    reverse = (sort_order == 'desc')
    if sort_by == 'name':
        all_items.sort(key=lambda x: x['name'].lower(), reverse=reverse)
    elif sort_by == 'size':
        all_items.sort(key=lambda x: x['size'] if x['size'] is not None else 0, reverse=reverse)
    elif sort_by == 'date':
        all_items.sort(key=lambda x: x['date'] if x['date'] is not None else datetime.min, reverse=reverse)
    elif sort_by == 'type':
        all_items.sort(key=lambda x: x['mime_type'].lower() if x['mime_type'] else '', reverse=reverse)
    elif sort_by == 'folder':
        all_items.sort(key=lambda x: x['folder'].lower(), reverse=reverse)
    all_items.sort(key=lambda x: 0 if x['type'] == 'folder' else 1)

    if per_page is not None:
        total_items = len(all_items)
        total_pages = int(math.ceil(total_items / per_page))
        start = (page - 1) * per_page
        end = start + per_page
        paginated_items = all_items[start:end]
    else:
        total_pages = 1
        paginated_items = all_items

    path_parts = current_folder_path.split('/')
    breadcrumbs = []
    for i, part in enumerate(path_parts):
        full_path_for_crumb = '/'.join(path_parts[:i+1])
        crumb_id = database.get_folder_id_by_path(full_path_for_crumb)
        breadcrumbs.append({'name': part, 'id': crumb_id})

    parent_folder_id = None
    if current_folder_path != 'root':
        parent_folder_path = os.path.dirname(current_folder_path)
        parent_folder_id = database.get_folder_id_by_path(parent_folder_path)

    return render_template('folders.html', 
                           items=paginated_items,
                           current_folder=current_folder_path,
                           breadcrumbs=breadcrumbs,
                           view_mode=view_mode,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           parent_folder_id=parent_folder_id,
                           current_folder_id=folder_id,
                           page=page,
                           per_page=per_page_str,
                           total_pages=total_pages,
                           pagination_endpoint='views.folders')

@views_bp.route('/create_folder', methods=['POST'])
def create_folder_route():
    folder_name = request.form.get('folder_name')
    current_folder = request.form.get('current_folder', 'root')
    if not folder_name:
        flash('Folder name cannot be empty.')
        return redirect(url_for('views.folders', folder_id=database.get_folder_id_by_path(current_folder)))
    new_folder_path = os.path.join(current_folder, folder_name).replace('\\', '/')
    try:
        database.create_folder(new_folder_path)
        flash(f'Folder "{new_folder_path}" created successfully.')
    except Exception as e:
        flash(f'Error creating folder: {e}')
    return redirect(url_for('views.folders', folder_id=database.get_folder_id_by_path(new_folder_path)))
    
@views_bp.route('/rename', methods=['POST'])
def rename_item_route():
    item_type = request.form.get('item_type')
    item_id = request.form.get('item_id')
    new_name = request.form.get('new_name')
    if not new_name:
        flash('New name cannot be empty.')
        return redirect(request.referrer or url_for('views.folders'))
    try:
        database.rename_item(item_id, new_name, item_type == 'folder')
        flash(f'Item renamed to "{new_name}" successfully.')
    except Exception as e:
        flash(f'Error renaming item: {e}')
    return redirect(request.referrer or url_for('views.folders'))

@views_bp.route('/bulk_rename', methods=['POST'])
def bulk_rename_route():
    items = json.loads(request.form.get('items'))
    rename_method = request.form.get('rename_method')
    new_name = request.form.get('new_name')
    rename_template = request.form.get('rename_template')
    find_string = request.form.get('find_string')
    replace_string = request.form.get('replace_string')
    try:
        database.bulk_rename_items(items, rename_method, new_name, rename_template, find_string, replace_string)
        flash(f'Items renamed successfully.')
    except Exception as e:
        flash(f'Error during bulk rename: {e}')
    return redirect(request.referrer or url_for('views.folders'))

@views_bp.route('/move', methods=['POST'])
def move_items_route():
    items = json.loads(request.form.get('items'))
    destination_folder = request.form.get('destination_folder')
    if not destination_folder:
        flash('Destination folder cannot be empty.')
        return redirect(request.referrer or url_for('views.folders'))
    try:
        database.move_items(items, destination_folder)
        flash(f'Items moved successfully.')
    except Exception as e:
        flash(f'Error moving items: {e}')
    return redirect(request.referrer or url_for('views.folders'))

@views_bp.route('/copy', methods=['POST'])
def copy_items_route():
    items = json.loads(request.form.get('items'))
    destination_folder = request.form.get('destination_folder')
    if not destination_folder:
        flash('Destination folder cannot be empty.')
        return redirect(request.referrer or url_for('views.folders'))
    try:
        database.copy_items(items, destination_folder)
        flash(f'Items copied successfully.')
    except Exception as e:
        flash(f'Error copying items: {e}')
    return redirect(request.referrer or url_for('views.folders'))

@views_bp.route('/delete', methods=['POST'])
def delete_item_route():
    item_ids_str = request.form.get('item_id_or_path')
    item_type = request.form.get('item_type') # The JS sends 'bulk' for bulk delete

    if not item_ids_str:
        flash('No items selected for deletion.', 'warning')
        return redirect(request.referrer or url_for('views.folders'))
    
    try:
        if item_type == 'bulk':
            items = json.loads(item_ids_str)
            # Extract the integer IDs from the list of dicts
            ids_to_delete = [int(item['id']) for item in items]
            database.delete_item(ids_to_delete, is_bulk=True)
        else:
            # Single item deletion
            ids_to_delete = [int(item_ids_str)]
            database.delete_item(ids_to_delete)
        
        flash('Items moved to recycle bin.', 'success')

    except Exception as e:
        flash(f'Error deleting items: {e}', 'danger')
        
    return redirect(request.referrer or url_for('views.folders'))

@views_bp.route('/recycle_bin')
def recycle_bin():
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    view_mode = request.args.get('view_mode', 'list')
    page = request.args.get('page', 1, type=int)
    per_page_str = request.args.get('per_page', '20')
    per_page = int(per_page_str) if per_page_str != 'all' else None

    deleted_items = database.get_deleted_items(sort_by, sort_order)

    all_items = []
    for item in deleted_items:
        if item.filename == '.folder_marker':
            all_items.append({'type': 'folder', 'obj': item, 'name': os.path.basename(item.folder), 'size': 0, 'date': item.upload_date, 'folder': item.folder, 'mime_type': 'folder'})
        else:
            all_items.append({'type': 'file', 'obj': item, 'name': item.filename, 'size': item.size, 'date': item.upload_date, 'folder': item.folder, 'mime_type': item.mime_type})

    reverse = (sort_order == 'desc')
    if sort_by == 'name':
        all_items.sort(key=lambda x: x['name'].lower(), reverse=reverse)
    elif sort_by == 'size':
        all_items.sort(key=lambda x: x['size'] if x['size'] is not None else 0, reverse=reverse)
    elif sort_by == 'date':
        all_items.sort(key=lambda x: x['date'] if x['date'] is not None else datetime.min, reverse=reverse)
    all_items.sort(key=lambda x: 0 if x['type'] == 'folder' else 1)

    if per_page is not None:
        total_items = len(all_items)
        total_pages = int(math.ceil(total_items / per_page))
        start = (page - 1) * per_page
        end = start + per_page
        paginated_items = all_items[start:end]
    else:
        total_pages = 1
        paginated_items = all_items

    return render_template('recycle_bin.html', 
                           items=paginated_items, 
                           sort_by=sort_by, 
                           sort_order=sort_order, 
                           view_mode=view_mode, 
                           page=page, 
                           per_page=per_page_str, 
                           total_pages=total_pages, 
                           pagination_endpoint='views.recycle_bin')

@views_bp.route('/restore_items', methods=['POST'])
def restore_items_route():
    items = json.loads(request.form.get('item_ids'))
    try:
        database.restore_items(items)
        flash(f'Restored {len(items)} item(s) from recycle bin.')
    except Exception as e:
        flash(f'Error restoring items: {e}')
    return redirect(request.referrer or url_for('views.recycle_bin'))

@views_bp.route('/permanent_delete_items', methods=['POST'])
def permanent_delete_items_route():
    items = json.loads(request.form.get('item_ids'))
    try:
        database.permanent_delete_items(items)
        flash(f'Permanently deleted {len(items)} item(s).')
    except Exception as e:
        flash(f'Error permanently deleting items: {e}')
    return redirect(request.referrer or url_for('views.recycle_bin'))

@views_bp.route('/empty_recycle_bin', methods=['POST'])
def empty_recycle_bin_route():
    try:
        database.empty_recycle_bin()
        return jsonify({'success': True, 'message': 'Recycle bin emptied successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@views_bp.route('/preview/<int:db_id>')
def preview_file(db_id):
    file = database.get_file_by_id(db_id)
    if not file or not file.message_link:
        flash('File not found or has no message link.')
        return redirect(url_for('views.index'))
    return redirect(file.message_link)

@views_bp.route('/thumbnail/<string:thumbnail_file_id>')
def get_thumbnail(thumbnail_file_id):
    cache_file_path = os.path.join(bot_handler.CACHE_DIR, thumbnail_file_id)
    if os.path.exists(cache_file_path):
        return send_file(cache_file_path, mimetype='image/jpeg')
    file_stream = bot_handler.stream_and_cache_telegram_file(thumbnail_file_id)
    return Response(file_stream, mimetype='image/jpeg')

@views_bp.route('/search')
def search():
    return render_template('search.html', 
                           results=[], 
                           query='', 
                           path='root', 
                           file_type='', 
                           min_size=None, 
                           min_size_unit='MB', 
                           max_size=None, 
                           max_size_unit='MB', 
                           start_date=None, 
                           end_date=None, 
                           sort_by=None, 
                           sort_order=None, 
                           view_mode='list', 
                           page=1, 
                           per_page='20', 
                           total_pages=1, 
                           pagination_endpoint='views.search_results')

@views_bp.route('/search_results')
def search_results():
    query = request.args.get('query', '')
    path = request.args.get('path', 'root')
    file_type = request.args.get('type', '')
    min_size_input = request.args.get('min_size', type=int)
    min_size_unit = request.args.get('min_size_unit', 'MB')
    max_size_input = request.args.get('max_size', type=int)
    max_size_unit = request.args.get('max_size_unit', 'MB')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    view_mode = request.args.get('view_mode', 'list')
    page = request.args.get('page', 1, type=int)
    per_page_str = request.args.get('per_page', '20')
    if per_page_str == 'all':
        per_page = None
    else:
        per_page = int(per_page_str)

    min_size = convert_size_to_bytes(min_size_input, min_size_unit)
    max_size = convert_size_to_bytes(max_size_input, max_size_unit)

    results = database.search_files(query, path, file_type, min_size, max_size, start_date, end_date, sort_by, sort_order)

    all_items = []
    for item in results:
        if item.filename == '.folder_marker':
            all_items.append({'type': 'folder', 'obj': item, 'name': os.path.basename(item.folder), 'size': 0, 'date': item.upload_date})
        else:
            all_items.append({'type': 'file', 'obj': item, 'name': item.filename, 'size': item.size, 'date': item.upload_date})

    all_items.sort(key=lambda x: 0 if x['type'] == 'folder' else 1)

    if per_page is not None:
        total_items = len(all_items)
        total_pages = int(math.ceil(total_items / per_page))
        start = (page - 1) * per_page
        end = start + per_page
        paginated_items = all_items[start:end]
    else:
        total_pages = 1
        paginated_items = all_items

    return render_template('search.html', 
                           items=paginated_items,
                           query=query,
                           path=path,
                           file_type=file_type,
                           min_size=min_size_input,
                           min_size_unit=min_size_unit,
                           max_size=max_size_input,
                           max_size_unit=max_size_unit,
                           start_date=start_date,
                           end_date=end_date,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           view_mode=view_mode,
                           page=page,
                           per_page=per_page_str,
                           total_pages=total_pages,
                           pagination_endpoint='views.search_results')

def convert_size_to_bytes(size, unit):
    if size is None:
        return None
    size = int(size)
    if unit == "B":
        return size
    elif unit == "KB":
        return size * 1024
    elif unit == "MB":
        return size * 1024 * 1024
    elif unit == "GB":
        return size * 1024 * 1024 * 1024
    return None
