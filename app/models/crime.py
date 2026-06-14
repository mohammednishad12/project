from datetime import datetime
from app import db


class Crime(db.Model):
    __tablename__ = 'crimes'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=True)
    type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    district = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time.isoformat() if self.time else None,
            'type': self.type,
            'description': self.description,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'district': self.district,
            'address': self.address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }