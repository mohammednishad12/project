from datetime import datetime
import bcrypt
from flask_login import UserMixin
from app import db


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='viewer')  # admin or viewer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw):
        self.password_hash = bcrypt.hashpw(raw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, raw):
        return bcrypt.checkpw(raw.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def is_admin(self):
        return self.role == 'admin'