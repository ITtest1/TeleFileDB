from flask import Flask, session
from models import db
import click
import os
import logging
import asyncio
import database
import threading

def create_app():
    # Create and configure the app
    app = Flask(__name__)

    # --- Logging Setup ---
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        # Create instance folder if it doesn't exist
        if not os.path.exists('instance'):
            os.makedirs('instance')
        # Log to a file
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=1024 * 1024 * 10, backupCount=5) # 10MB per file, 5 backups
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('TeleFileDB startup')
        logging.getLogger("pyrogram").setLevel(logging.WARNING)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///files.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.urandom(24)

    # Initialize extensions
    db.init_app(app)

    # Check if database needs to be initialized
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if not inspector.has_table("files"):
            click.echo("Database tables not found, creating them now...")
            db.create_all()
            click.echo("Database tables created.")

        # Check if admin user needs to be created
        from models import User
        if not User.query.first():
            click.echo("No users found, creating admin user...")
            from config import ADMIN_USERNAME, ADMIN_PASSWORD
            from database import add_user
            add_user(ADMIN_USERNAME, ADMIN_PASSWORD)
            click.echo(f"Admin user '{ADMIN_USERNAME}' created.")

    # Jinja2 extensions and filters
    app.jinja_env.add_extension('jinja2.ext.do')
    app.jinja_env.filters['basename'] = os.path.basename
    app.jinja_env.filters['format_size'] = format_size

    # Register blueprints
    from app_blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app_blueprints.admin import admin_bp
    app.register_blueprint(admin_bp)

    from app_blueprints.api import api_bp
    app.register_blueprint(api_bp)

    from app_blueprints.views import views_bp
    app.register_blueprint(views_bp)

    # Register CLI commands
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin_command)

    # Context processors
    @app.context_processor
    def inject_user():
        if 'user_id' in session:
            user = database.get_user_by_id(session['user_id'])
            if user:
                return dict(user=user, is_admin=(user.username == 'admin'))
        return dict(user=None, is_admin=False)

    return app

@click.command("init-db")
def init_db_command():
    """Clear the existing data and create new tables."""
    db.create_all()
    click.echo('Initialized the database.')

@click.command("create-admin")
def create_admin_command():
    """Creates the admin user."""
    from config import ADMIN_USERNAME, ADMIN_PASSWORD
    from database import add_user, get_user_by_username
    if get_user_by_username(ADMIN_USERNAME):
        click.echo('Admin user already exists.')
        return
    add_user(ADMIN_USERNAME, ADMIN_PASSWORD)
    click.echo('Admin user created.')

def format_size(size_bytes):
    import math
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

app = create_app()

# --- Background Cache Cleaner ---
def cache_cleanup_worker():
    from bot_handler import clean_cache
    from config import CACHE_CLEANUP_INTERVAL_MINUTES
    import time
    
    logging.info(f"Cache cleanup worker started. Will run every {CACHE_CLEANUP_INTERVAL_MINUTES} minutes.")
    while True:
        time.sleep(CACHE_CLEANUP_INTERVAL_MINUTES * 60)
        logging.info("Running scheduled cache cleanup...")
        clean_cache()

from bot_handler import pyrogram_runner

if __name__ == '__main__':
    from config import CACHE_CLEANUP_INTERVAL_MINUTES
    # Start the cache cleanup worker in a background thread if interval is set
    if CACHE_CLEANUP_INTERVAL_MINUTES > 0:
        cleanup_thread = threading.Thread(target=cache_cleanup_worker, daemon=True)
        cleanup_thread.start()
    else:
        logging.info("Automatic cache cleanup is disabled.")

    # Start the Pyrogram Runner
    logging.info("Starting Pyrogram Runner...")
    pyrogram_runner.start()

    logging.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

