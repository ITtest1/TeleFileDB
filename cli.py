import click
from database import init_db, add_file, create_folder, rename_item, add_vip_user, remove_vip_user, get_all_vip_users, move_items, copy_items, restore_items, permanent_delete_items, empty_recycle_bin, delete_item # Moved delete_item to end
from user_handler import scan_channel_history
from config import TELEGRAM_CHAT_ID
import asyncio
import os
import json
import base64 # Added for decoding JSON from app.py

@click.group()
def cli():
    pass

@click.command()
def initdb():
    """Initialize the database."""
    init_db()
    click.echo('Initialized the database.')

@click.command()
@click.option('--chat_id', default=TELEGRAM_CHAT_ID, help='Telegram Chat ID to scan.')
def scan_history(chat_id):
    """Scan Telegram channel/group history for files."""
    click.echo(f'Starting to scan history for chat ID: {chat_id}')
    asyncio.run(scan_channel_history(chat_id, add_file))
    click.echo('History scan complete.')

@click.command()
@click.argument('folder_path')
def create_folder_cli(folder_path):
    """Create a new folder in the drive."""
    from app import app # Import app here to avoid circular dependency
    with app.app_context():
        create_folder(folder_path)
    click.echo(f'Folder "{folder_path}" created.')

@click.command()
@click.argument('item_id') # This will be the DB ID for files, or path for folders
@click.argument('new_name')
@click.option('--is_folder', is_flag=True, help='Set if renaming a folder.')
@click.option('--current_folder', default=None, help='Current folder path for folder renaming.')
def rename(item_id, new_name, is_folder, current_folder):
    """Rename a file or folder."""
    from app import app
    with app.app_context():
        # item_id is already the correct DB ID for files, or path for folders
        rename_item(item_id, new_name, is_folder=is_folder, current_folder=current_folder)
    click.echo(f'Renamed "{item_id}" to "{new_name}".')

# Removed the old 'move' command as it's replaced by 'move_bulk' and the logic is now in database.py

@click.command()
@click.argument('item_id') # This will be the DB ID for files, or path for folders
@click.option('--is_folder', is_flag=True, help='Set if deleting a folder.') # Keep for now to differentiate single file/folder delete
def delete(item_id, is_folder): # Removed db_only as it's now always logical delete
    """Delete a file or folder (moves to recycle bin)."""
    from app import app
    with app.app_context():
        # For single delete, item_id is the DB ID for files, or path for folders
        # The delete_item function in database.py now handles the logic based on item_type
        # We need to pass a list of dictionaries for delete_item to handle it uniformly
        if is_folder:
            # For folders, item_id is the folder path
            items_to_delete = [{'id': item_id, 'type': 'folder'}]
        else:
            # For files, item_id is the DB ID
            items_to_delete = [{'id': int(item_id), 'type': 'file'}] # Ensure ID is int for files

        delete_item(items_to_delete, is_bulk=True) # Treat single delete as bulk for consistency
    click.echo(f'Moved "{item_id}" to recycle bin.')

@click.command()
@click.argument('user_id', type=int)
def add_vip(user_id):
    """Add a user to the VIP list."""
    from app import app
    with app.app_context():
        add_vip_user(user_id)
    click.echo(f'User {user_id} added as VIP.')

@click.command()
@click.argument('user_id', type=int)
def remove_vip(user_id):
    """Remove a user from the VIP list."""
    from app import app
    with app.app_context():
        remove_vip_user(user_id)
    click.echo(f'User {user_id} removed from VIPs.')

@click.command()
def list_vips():
    """List all VIP users."""
    from app import app
    with app.app_context():
        vips = get_all_vip_users()
    if vips:
        click.echo("VIP Users:")
        for user_id in vips:
            click.echo(f'- {user_id}')
    else:
        click.echo("No VIP users found.")

@click.command()
@click.argument('items_json')
@click.argument('destination_folder')
def move_bulk(items_json, destination_folder):
    """Move multiple files or folders."""
    decoded_items_json = base64.b64decode(items_json).decode('utf-8')
    items = json.loads(decoded_items_json)
    from app import app
    with app.app_context():
        move_items(items, destination_folder)
    click.echo(f'Moved {len(items)} items to "{destination_folder}".')

@click.command()
@click.argument('items_json')
@click.argument('destination_folder')
def copy_bulk(items_json, destination_folder):
    """Copy multiple files or folders."""
    decoded_items_json = base64.b64decode(items_json).decode('utf-8')
    items = json.loads(decoded_items_json)
    from app import app
    with app.app_context():
        copy_items(items, destination_folder)
    click.echo(f'Copied {len(items)} items to "{destination_folder}".')

@click.command()
@click.argument('items_json')
def delete_bulk(items_json): # Removed db_only as it's now always logical delete
    """Delete multiple files or folders (moves to recycle bin)."""
    items = json.loads(items_json)
    from app import app
    with app.app_context():
        delete_item(items, is_bulk=True)
    click.echo(f'Moved {len(items)} items to recycle bin.')

@click.command()
@click.argument('item_ids_json')
def restore_bulk(item_ids_json):
    """Restore multiple items from the recycle bin."""
    item_ids = json.loads(item_ids_json)
    from app import app
    with app.app_context():
        restore_items(item_ids)
    click.echo(f'Restored {len(item_ids)} items from recycle bin.')

@click.command()
@click.argument('item_ids_json')
def permanent_delete_bulk(item_ids_json):
    """Permanently delete multiple items from the recycle bin."""
    item_ids = json.loads(item_ids_json)
    from app import app
    with app.app_context():
        permanent_delete_items(item_ids)
    click.echo(f'Permanently deleted {len(item_ids)} items.')

@click.command()
def empty_recycle_bin():
    """Empty the recycle bin, permanently deleting all items."""
    from app import app
    with app.app_context():
        empty_recycle_bin()
    click.echo('Recycle bin emptied.')


cli.add_command(initdb)
cli.add_command(scan_history)
cli.add_command(create_folder_cli)
cli.add_command(rename)
# cli.add_command(move) # Removed
cli.add_command(delete)
cli.add_command(add_vip)
cli.add_command(remove_vip)
cli.add_command(list_vips)
cli.add_command(move_bulk)
cli.add_command(copy_bulk)
cli.add_command(delete_bulk)
cli.add_command(restore_bulk) # Added
cli.add_command(permanent_delete_bulk) # Added
cli.add_command(empty_recycle_bin) # Added

if __name__ == '__main__':
    cli()