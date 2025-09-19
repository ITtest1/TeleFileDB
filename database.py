from models import db, File, User, UserPath
from sqlalchemy import and_, or_, not_
import logging
import os

def get_all_files(sort_by='date', sort_order='desc'):
    query = File.query.filter(File.filename != '.folder_marker', File.is_deleted == False)
    if sort_by and sort_order:
        if sort_by == 'name':
            order = File.filename.desc() if sort_order == 'desc' else File.filename.asc()
        elif sort_by == 'size':
            order = File.size.desc() if sort_order == 'desc' else File.size.asc()
        elif sort_by == 'date':
            order = File.upload_date.desc() if sort_order == 'desc' else File.upload_date.asc()
        elif sort_by == 'type':
            order = File.mime_type.desc() if sort_order == 'desc' else File.mime_type.asc()
        elif sort_by == 'folder':
            order = File.folder.desc() if sort_order == 'desc' else File.folder.asc()
        else:
            order = File.upload_date.desc()
        query = query.order_by(order)
    return query.all()

def add_file(filename, file_id, folder, size=None, mime_type=None, thumbnail_file_id=None, message_link=None):
    new_file = File(
        filename=filename, 
        file_id=file_id, 
        folder=folder, 
        size=size, 
        mime_type=mime_type, 
        thumbnail_file_id=thumbnail_file_id, 
        message_link=message_link
    )
    db.session.add(new_file)
    db.session.commit()

def get_files_by_folder(folder):
    return File.query.filter_by(folder=folder, is_deleted=False).all()

def get_all_folders():
    return [r[0] for r in db.session.query(File.folder).filter(File.is_deleted == False).distinct()]

def _ensure_folder_path_exists(folder_path):
    """
    Ensures that all parent folders for a given path exist in the database as .folder_marker files.
    If they don't exist, they are created.
    """
    if not folder_path or folder_path == 'root':
        return
    
    parts = folder_path.split('/')
    current_path = ''
    for part in parts:
        if current_path == '':
            current_path = part
        else:
            current_path = f"{current_path}/{part}"
        
        # Use SQLAlchemy session to query for the folder marker
        folder_marker = File.query.filter_by(folder=current_path, filename='.folder_marker').first()
        
        if not folder_marker:
            # Use the existing SQLAlchemy-based create_folder function
            create_folder(current_path)

def create_folder(folder_path):
    new_folder = File(filename=".folder_marker", file_id="FOLDER_MARKER", folder=folder_path, mime_type="application/x-folder")
    db.session.add(new_folder)
    db.session.commit()

def delete_item(item_ids, is_bulk=False):
    if not isinstance(item_ids, list):
        item_ids = [item_ids]

    for item_id in item_ids:
        item = File.query.get(item_id)
        if item:
            if item.filename == '.folder_marker':
                # This is a folder. Mark the folder and all its contents as deleted.
                folder_path = item.folder
                File.query.filter(or_(File.folder == folder_path, File.folder.like(f'{folder_path}/%'))).update(
                    {File.is_deleted: True}, synchronize_session=False
                )
            else:
                # This is a file. Mark it as deleted.
                item.is_deleted = True
    db.session.commit()

def rename_item(item_id, new_name, is_folder=False, current_folder=None):
    item = File.query.get(item_id)
    if not item:
        return

    if is_folder:
        old_full_path = item.folder
        parent_path = os.path.dirname(old_full_path)
        new_full_path = os.path.join(parent_path, new_name).replace('\\', '/')
        # Update all affected paths
        files_to_update = File.query.filter(or_(File.folder == old_full_path, File.folder.like(old_full_path + '%'))).all()
        for file_to_update in files_to_update:
            file_to_update.folder = file_to_update.folder.replace(old_full_path, new_full_path, 1)
    else:
        item.filename = new_name
    db.session.commit()

def move_items(items, destination_folder):
    destination_folder = destination_folder.strip('/')
    # Ensure destination folder exists
    dest_folder_obj = File.query.filter_by(folder=destination_folder, filename='.folder_marker').first()
    if not dest_folder_obj and destination_folder != 'root':
        _ensure_folder_path_exists(destination_folder)

    for item_data in items:
        item = File.query.get(item_data['id'])
        if not item:
            continue
        
        if item_data['type'] == 'file':
            item.folder = destination_folder
        elif item_data['type'] == 'folder':
            old_folder_path = item.folder
            folder_name = os.path.basename(old_folder_path)
            new_folder_path = os.path.join(destination_folder, folder_name).replace('\\', '/')

            # Find all files and subfolders to move
            files_to_move = File.query.filter(File.folder.like(old_folder_path + '%')).all()
            for file_to_move in files_to_move:
                # Replace the old path prefix with the new one
                new_file_folder = file_to_move.folder.replace(old_folder_path, new_folder_path, 1)
                file_to_move.folder = new_file_folder

    db.session.commit()

def copy_items(items, destination_folder):
    destination_folder = destination_folder.strip('/')
    # Ensure destination folder exists
    dest_folder_obj = File.query.filter_by(folder=destination_folder, filename='.folder_marker').first()
    if not dest_folder_obj and destination_folder != 'root':
        _ensure_folder_path_exists(destination_folder)

    for item_data in items:
        item = File.query.get(item_data['id'])
        if not item:
            continue

        if item_data['type'] == 'file':
            new_file = File(
                filename=item.filename,
                file_id=item.file_id,
                folder=destination_folder,
                size=item.size,
                mime_type=item.mime_type,
                thumbnail_file_id=item.thumbnail_file_id,
                message_link=item.message_link
            )
            db.session.add(new_file)
        elif item_data['type'] == 'folder':
            old_folder_path = item.folder
            folder_name = os.path.basename(old_folder_path)
            new_folder_path = os.path.join(destination_folder, folder_name).replace('\\', '/')

            # Find all files and subfolders to copy
            items_to_copy = File.query.filter(File.folder.like(old_folder_path + '%')).all()
            for item_to_copy in items_to_copy:
                new_item_folder = item_to_copy.folder.replace(old_folder_path, new_folder_path, 1)
                new_item = File(
                    filename=item_to_copy.filename,
                    file_id=item_to_copy.file_id,
                    folder=new_item_folder,
                    size=item_to_copy.size,
                    mime_type=item_to_copy.mime_type,
                    thumbnail_file_id=item_to_copy.thumbnail_file_id,
                    message_link=item_to_copy.message_link
                )
                db.session.add(new_item)

    db.session.commit()

def bulk_rename_items(items, rename_method, new_name=None, rename_template=None, find_string=None, replace_string=None):
    for i, item_data in enumerate(items):
        item = File.query.get(item_data['id'])
        if not item:
            continue

        original_name = os.path.basename(item.folder) if item_data['type'] == 'folder' else item.filename
        name, ext = os.path.splitext(original_name)

        if rename_method == 'new_name':
            final_name = new_name
        elif rename_method == 'template':
            final_name = rename_template.replace('{i}', str(i+1)).replace('{name}', name).replace('{ext}', ext)
        elif rename_method == 'find_replace':
            final_name = original_name.replace(find_string, replace_string)
        else:
            continue # Should not happen

        if item_data['type'] == 'folder':
            old_full_path = item.folder
            parent_path = os.path.dirname(old_full_path)
            new_full_path = os.path.join(parent_path, final_name).replace('\\', '/')
            
            files_to_update = File.query.filter(File.folder.like(old_full_path + '%')).all()
            for file_to_update in files_to_update:
                file_to_update.folder = file_to_update.folder.replace(old_full_path, new_full_path, 1)
        else:
            item.filename = final_name

    db.session.commit()

def get_file_by_id(db_id):
    return File.query.get(db_id)

def get_db_id_by_file_id(file_id):
    file = File.query.filter_by(file_id=file_id, is_deleted=False).first()
    return file.id if file else None

def get_filename_by_telegram_file_id(telegram_file_id, include_deleted=False):
    query = File.query.filter_by(file_id=telegram_file_id)
    if not include_deleted:
        query = query.filter_by(is_deleted=False)
    file = query.first()
    return file.filename if file else None

def get_file_by_telegram_file_id(telegram_file_id, include_deleted=False):
    query = File.query.filter_by(file_id=telegram_file_id)
    if not include_deleted:
        query = query.filter_by(is_deleted=False)
    return query.first()

def get_file_by_telegram_file_id_including_deleted(telegram_file_id):
    return File.query.filter_by(file_id=telegram_file_id).first()

def get_root_folder_id():
    file = File.query.filter_by(folder='root', filename='.folder_marker', is_deleted=False).first()
    return file.id if file else None

def get_folder_id_by_path(folder_path):
    file = File.query.filter_by(folder=folder_path, filename='.folder_marker', is_deleted=False).first()
    return file.id if file else None

def get_folder_contents(current_folder):
    files = File.query.filter_by(folder=current_folder, is_deleted=False).filter(File.filename != '.folder_marker').all()

    if current_folder == 'root':
        like_path = 'root/%'
    else:
        like_path = current_folder + '/%'
        
    all_subfolders_query = File.query.filter(
        File.folder.like(like_path),
        File.filename == '.folder_marker',
        File.is_deleted == False
    )
    
    direct_subfolders = []
    for sub in all_subfolders_query.all():
        parent_path = os.path.dirname(sub.folder)
        if parent_path == current_folder:
            direct_subfolders.append(sub)
            
    subfolders = direct_subfolders
    
    return files, subfolders

def get_folder_contents_for_user(user_id, current_folder, sort_by=None, sort_order=None):
    user = get_user_by_id(user_id)
    allowed_paths = [p.path for p in user.paths]

    if user.username != 'admin':
        can_access = any(current_folder.startswith(p) for p in allowed_paths) or \
                     any(p.startswith(current_folder + '/') for p in allowed_paths)
        if not can_access:
            return None, None

    files, subfolders = get_folder_contents(current_folder)

    if user.username != 'admin':
        allowed_subfolders = []
        for subfolder in subfolders:
            if any(subfolder.folder.startswith(p) for p in allowed_paths) or \
               any(p.startswith(subfolder.folder + '/') for p in allowed_paths):
                allowed_subfolders.append(subfolder)
        subfolders = allowed_subfolders

    return files, subfolders

def get_all_files_in_folder(folder_path):
    return File.query.filter(File.folder.like(f'{folder_path}%')).all()


def get_all_files_for_user(user_id, sort_by=None, sort_order=None):
    user = get_user_by_id(user_id)
    if user.username == 'admin':
        return get_all_files(sort_by, sort_order)
    
    allowed_paths = [p.path for p in user.paths]
    if not allowed_paths:
        return []

    query = File.query.filter(File.is_deleted == False, or_(*[File.folder.like(p + '%') for p in allowed_paths]))
    # ... (implement sorting)
    return query.all()

def search_files(query, path, file_type, min_size=None, max_size=None, start_date=None, end_date=None, sort_by=None, sort_order=None):
    q = File.query.filter(File.is_deleted == False)
    
    if query:
        q = q.filter(File.filename.like(f'%{query}%'))
    
    if path and path != 'root':
        q = q.filter(File.folder.like(f'{path}%'))
    
    if file_type:
        if file_type == 'folder':
            q = q.filter(File.filename == '.folder_marker')
        else:
            q = q.filter(File.mime_type.like(f'{file_type}%'))

    if min_size is not None:
        q = q.filter(File.size >= min_size)
        
    if max_size is not None:
        q = q.filter(File.size <= max_size)
        
    if start_date:
        q = q.filter(File.upload_date >= start_date)
        
    if end_date:
        q = q.filter(File.upload_date <= end_date)

    if sort_by and sort_order:
        if sort_by == 'name':
            if sort_order == 'asc':
                q = q.order_by(File.filename.asc())
            else:
                q = q.order_by(File.filename.desc())
        elif sort_by == 'size':
            if sort_order == 'asc':
                q = q.order_by(File.size.asc())
            else:
                q = q.order_by(File.size.desc())
        elif sort_by == 'date':
            if sort_order == 'asc':
                q = q.order_by(File.upload_date.asc())
            else:
                q = q.order_by(File.upload_date.desc())
        elif sort_by == 'type':
            if sort_order == 'asc':
                q = q.order_by(File.mime_type.asc())
            else:
                q = q.order_by(File.mime_type.desc())
        elif sort_by == 'folder':
            if sort_order == 'asc':
                q = q.order_by(File.folder.asc())
            else:
                q = q.order_by(File.folder.desc())

    return q.all()

def get_deleted_items(sort_by='date', sort_order='desc'):
    query = File.query.filter_by(is_deleted=True)
    if sort_by and sort_order:
        if sort_by == 'name':
            order = File.filename.desc() if sort_order == 'desc' else File.filename.asc()
        elif sort_by == 'size':
            order = File.size.desc() if sort_order == 'desc' else File.size.asc()
        elif sort_by == 'date':
            order = File.upload_date.desc() if sort_order == 'desc' else File.upload_date.asc()
        elif sort_by == 'type':
            order = File.mime_type.desc() if sort_order == 'desc' else File.mime_type.asc()
        elif sort_by == 'folder':
            order = File.folder.desc() if sort_order == 'desc' else File.folder.asc()
        else:
            order = File.upload_date.desc()
        query = query.order_by(order)
    return query.all()

def restore_items(items):
    # Use a set to keep track of file IDs we've already processed to avoid redundant DB calls
    processed_ids = set()
    items_to_process = [int(item['id']) for item in items]

    while items_to_process:
        item_id = items_to_process.pop(0)
        if item_id in processed_ids:
            continue

        item = File.query.get(item_id)
        if not item:
            continue

        # 1. Restore the item itself and mark as processed
        item.is_deleted = False
        processed_ids.add(item.id)

        # 2. If it's a folder, find all its contents and add them to the list to be restored
        if item.filename == '.folder_marker':
            folder_path = item.folder
            children = File.query.filter(
                or_(File.folder == folder_path, File.folder.like(f'{folder_path}/%'))
            ).filter(File.is_deleted == True).all()

            for child in children:
                if child.id not in processed_ids:
                    # We don't restore the child immediately, but add it to the list
                    # to ensure its parents are also handled if needed.
                    items_to_process.append(child.id)

        # 3. Ensure all parent folders of the restored item exist and are not deleted
        parent_path = item.folder
        if parent_path != 'root':
            parts = parent_path.split('/')
            current_path = ''
            for part in parts:
                if current_path == '':
                    current_path = part
                else:
                    current_path = f"{current_path}/{part}"
                
                # Find the folder marker for this path
                parent_folder_marker = File.query.filter_by(folder=current_path, filename='.folder_marker').first()
                if parent_folder_marker and parent_folder_marker.is_deleted:
                    parent_folder_marker.is_deleted = False
                    processed_ids.add(parent_folder_marker.id)

    db.session.commit()

def permanent_delete_items(items):
    for item in items:
        item_id = int(item['id'])
        file = File.query.get(item_id)
        if file:
            db.session.delete(file)
    db.session.commit()

def empty_recycle_bin():
    File.query.filter_by(is_deleted=True).delete()
    db.session.commit()

def clear_database():
    db.drop_all()
    db.create_all()

def is_file_deleted(telegram_file_id):
    file = get_file_by_telegram_file_id(telegram_file_id, include_deleted=True)
    return file.is_deleted if file else False

def get_user_by_username(username):
    return User.query.filter_by(username=username).first()

def get_user_by_id(user_id):
    return User.query.get(user_id)

def get_all_users():
    return User.query.all()

def get_user_paths(user_id):
    return [p.path for p in UserPath.query.filter_by(user_id=user_id).all()]

def add_user(username, password):
    new_user = User(username=username, password=password) # Note: password should be hashed
    db.session.add(new_user)
    db.session.commit()
    return new_user

def delete_user(user_id):
    user = get_user_by_id(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()

def update_user_paths(user_id, paths):
    UserPath.query.filter_by(user_id=user_id).delete()
    for path in paths:
        new_path = UserPath(user_id=user_id, path=path)
        db.session.add(new_path)
    db.session.commit()


