from datetime import datetime
from app import db


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parameters_json = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    format = db.Column(db.String(10), nullable=False)  # pdf or csv
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'parameters_json': self.parameters_json,
            'file_path': self.file_path,
            'format': self.format,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }