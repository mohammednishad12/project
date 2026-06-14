# ML Module for Crime Prediction System
#
# This module provides ML prediction utilities including:
# - Crime type classification (Random Forest)
# - Crime count regression (Linear Regression)
# - Time-series forecasting (LSTM)
#
# Usage:
#   from app.ml.predict import load_models, predict_crime_type, predict_crime_count, predict_lstm_forecast
#
#   models = load_models()
#   result = predict_crime_type(lat, lng, hour, day_of_week, month, district)

from .predict import (
    load_models,
    predict_crime_type,
    predict_crime_count,
    predict_lstm_forecast
)

__all__ = [
    'load_models',
    'predict_crime_type',
    'predict_crime_count',
    'predict_lstm_forecast'
]