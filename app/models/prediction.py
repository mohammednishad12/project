from datetime import datetime
from app import db


class Prediction(db.Model):
    __tablename__ = 'predictions'

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(50), nullable=False)
    location_lat = db.Column(db.Float, nullable=True)
    location_lng = db.Column(db.Float, nullable=True)
    predicted_type = db.Column(db.String(100), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    prediction_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'model_name': self.model_name,
            'location_lat': self.location_lat,
            'location_lng': self.location_lng,
            'predicted_type': self.predicted_type,
            'confidence': self.confidence,
            'prediction_date': self.prediction_date.isoformat() if self.prediction_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }