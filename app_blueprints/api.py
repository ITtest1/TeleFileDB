from flask import Blueprint, jsonify, request
import database
import bot_handler
import os
import threading

api_bp = Blueprint('api', __name__, url_prefix='/api')

# --- Cache Control APIs ---

@api_bp.route('/cache_file/<string:telegram_file_id>', methods=['POST'])
def cache_file_route(telegram_file_id):
    # Use a simple in-memory dict to track threads. For a more robust solution,
    # a proper task queue like Celery or Redis Queue would be better.
    if not hasattr(cache_file_route, "cache_threads"):
        cache_file_route.cache_threads = {}

    if telegram_file_id in cache_file_route.cache_threads and cache_file_route.cache_threads[telegram_file_id].is_alive():
        return jsonify({'success': False, 'message': 'Caching is already in progress for this file.'}), 409

    thread = threading.Thread(target=bot_handler.download_file_to_cache, args=(telegram_file_id,))
    thread.start()
    cache_file_route.cache_threads[telegram_file_id] = thread
    
    return jsonify({'success': True, 'message': f'Started caching file {telegram_file_id} in the background.'})

@api_bp.route('/cache_status/<string:telegram_file_id>', methods=['GET'])
def cache_status_route(telegram_file_id):
    file_info = database.get_file_by_telegram_file_id(telegram_file_id)
    if not file_info or not file_info.size:
        return jsonify({'status': 'error', 'message': 'File not found or file size is unknown.'}), 404

    total_size = file_info.size
    cache_file_path = os.path.join(bot_handler.CACHE_DIR, telegram_file_id)

    if not os.path.exists(cache_file_path):
        return jsonify({'status': 'not_cached', 'cached_bytes': 0, 'total_bytes': total_size})

    cached_size = os.path.getsize(cache_file_path)

    if cached_size >= total_size:
        return jsonify({'status': 'completed', 'cached_bytes': cached_size, 'total_bytes': total_size})
    else:
        return jsonify({'status': 'caching', 'cached_bytes': cached_size, 'total_bytes': total_size})

# --- Upload Task APIs ---

@api_bp.route('/tasks')
def get_tasks_api():
    tasks = database.get_upload_tasks()
    return jsonify([task.to_dict() for task in tasks])

@api_bp.route('/tasks/bulk_update_status', methods=['POST'])
def bulk_update_task_status_api():
    data = request.get_json()
    task_ids = data.get('task_ids')
    status = data.get('status')
    database.bulk_update_upload_task_status(task_ids, status)
    return jsonify(success=True)

@api_bp.route('/tasks/bulk_delete', methods=['POST'])
def bulk_delete_tasks_api():
    data = request.get_json()
    task_ids = data.get('task_ids')
    database.bulk_delete_upload_tasks(task_ids)
    return jsonify(success=True)

@api_bp.route('/tasks/update_status', methods=['POST'])
def update_task_status_route_api():
    data = request.get_json()
    task_id = data.get('task_id')
    status = data.get('status')
    database.update_upload_task_status(task_id, status)
    return jsonify(success=True)

@api_bp.route('/tasks/delete', methods=['POST'])
def delete_task_api():
    data = request.get_json()
    task_id = data.get('task_id')
    database.delete_upload_task(task_id)
    return jsonify(success=True)

@api_bp.route('/tasks/update_priority', methods=['POST'])
def update_task_priority_route_api():
    data = request.get_json()
    task_id = data.get('task_id')
    priority = data.get('priority')
    database.update_upload_task_priority(task_id, priority)
    return jsonify(success=True)
