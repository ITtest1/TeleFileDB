from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class File(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String, nullable=False)
    file_id = db.Column(db.String, nullable=False)
    folder = db.Column(db.String, nullable=False, index=True)
    size = db.Column(db.Integer)
    mime_type = db.Column(db.String)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    thumbnail_file_id = db.Column(db.String)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False, index=True)
    cover_file_id = db.Column(db.String)
    message_link = db.Column(db.String)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    paths = db.relationship('UserPath', backref='user', cascade="all, delete-orphan")

class UserPath(db.Model):
    __tablename__ = 'user_paths'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    path = db.Column(db.String, nullable=False)


