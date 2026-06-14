from app import db
from app.models.crime import Crime
from app.models.user import User
from app.models.prediction import Prediction
from app.models.report import Report

__all__ = ['db', 'Crime', 'User', 'Prediction', 'Report']