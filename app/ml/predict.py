"""
Prediction Utilities for Crime Data

Provides prediction functions for:
- Crime type classification (Random Forest)
- Crime count prediction (Linear Regression)
- Time-series forecasting (LSTM)
"""

import os
import sys
import logging
from datetime import datetime, timedelta

import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import joblib

# TensorFlow/Keras - handle import errors gracefully
try:
    import tensorflow as tf
    tf.get_logger().setLevel('ERROR')
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model directory
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')


class ModelsContainer:
    """Container for loaded ML models."""
    
    def __init__(self):
        self.rf_model = None
        self.lr_model = None
        self.lstm_model = None
        self.label_encoder = None
        self.district_encoder = None
        self.scaler = None
        self.loaded = False
    
    def is_loaded(self):
        return self.loaded


# Global models instance
_models = ModelsContainer()


def load_models():
    """
    Load all trained models from the models directory.
    
    Returns:
        ModelsContainer: Container with loaded models, or None if any model fails to load.
    
    Raises:
        Logs warning and returns None if model files are not found.
    """
    global _models
    
    if _models.is_loaded():
        return _models
    
    models_dir = MODELS_DIR
    
    # Load Random Forest model
    rf_path = os.path.join(models_dir, 'crime_type_rf.pkl')
    if os.path.exists(rf_path):
        try:
            _models.rf_model = joblib.load(rf_path)
            logger.info(f"Loaded Random Forest model from {rf_path}")
        except Exception as e:
            logger.warning(f"Failed to load Random Forest model: {e}")
            _models.rf_model = None
    else:
        logger.warning(f"Random Forest model not found: {rf_path}")
    
    # Load label encoder for crime types
    le_path = os.path.join(models_dir, 'crime_type_label_encoder.pkl')
    if os.path.exists(le_path):
        try:
            _models.label_encoder = joblib.load(le_path)
            logger.info(f"Loaded label encoder from {le_path}")
        except Exception as e:
            logger.warning(f"Failed to load label encoder: {e}")
            _models.label_encoder = None
    else:
        logger.warning(f"Label encoder not found: {le_path}")
    
    # Load Linear Regression model
    lr_path = os.path.join(models_dir, 'crime_count_lr.pkl')
    if os.path.exists(lr_path):
        try:
            _models.lr_model = joblib.load(lr_path)
            logger.info(f"Loaded Linear Regression model from {lr_path}")
        except Exception as e:
            logger.warning(f"Failed to load Linear Regression model: {e}")
            _models.lr_model = None
    else:
        logger.warning(f"Linear Regression model not found: {lr_path}")

    # Load district encoder
    de_path = os.path.join(models_dir, 'district_encoder.pkl')
    if os.path.exists(de_path):
        try:
            _models.district_encoder = joblib.load(de_path)
            logger.info(f"Loaded district encoder from {de_path}")
        except Exception as e:
            logger.warning(f"Failed to load district encoder: {e}")
            _models.district_encoder = None
    else:
        logger.warning(f"District encoder not found: {de_path}")

    # Load LSTM model and scaler
    if TF_AVAILABLE:
        lstm_path = os.path.join(models_dir, 'crime_lstm.h5')
        if os.path.exists(lstm_path):
            try:
                _models.lstm_model = tf.keras.models.load_model(lstm_path)
                logger.info(f"Loaded LSTM model from {lstm_path}")
            except Exception as e:
                logger.warning(f"Failed to load LSTM model: {e}")
                _models.lstm_model = None
        else:
            logger.warning(f"LSTM model not found: {lstm_path}")
        
        scaler_path = os.path.join(models_dir, 'crime_scaler.pkl')
        if os.path.exists(scaler_path):
            try:
                _models.scaler = joblib.load(scaler_path)
                logger.info(f"Loaded scaler from {scaler_path}")
            except Exception as e:
                logger.warning(f"Failed to load scaler: {e}")
                _models.scaler = None
        else:
            logger.warning(f"Scaler not found: {scaler_path}")
    else:
        logger.warning("TensorFlow not available, LSTM model not loaded")
    
    _models.loaded = True
    
    # Return None if no models were loaded
    if not any([_models.rf_model, _models.lr_model, _models.lstm_model]):
        logger.error("No models could be loaded")
        return None
    
    return _models


def prepare_district_encoding(district, district_encoder):
    """
    Encode a district string using the fitted label encoder.
    Returns encoded value or 0 (Unknown) if district not in encoder.
    """
    if district is None or district_encoder is None:
        return 0
    
    try:
        return district_encoder.transform([district])[0]
    except ValueError:
        # District not seen during training, return 0 (Unknown)
        return 0


def inverse_transform_prediction(prediction, label_encoder):
    """
    Transform encoded prediction back to original label.
    """
    if prediction is None or label_encoder is None:
        return "Unknown"
    
    try:
        if hasattr(prediction, '__iter__') and not isinstance(prediction, str):
            # Array of predictions
            return [label_encoder.inverse_transform([p])[0] for p in prediction]
        else:
            return label_encoder.inverse_transform([prediction])[0]
    except Exception:
        return "Unknown"


def predict_crime_type(lat, lng, hour, day_of_week, month, district):
    """
    Predict crime type based on location and time features.
    
    Args:
        lat (float): Latitude
        lng (float): Longitude
        hour (int): Hour of day (0-23)
        day_of_week (int): Day of week (0=Monday, 6=Sunday)
        month (int): Month (1-12)
        district (str): District name
    
    Returns:
        dict: {predicted_type: str, confidence: float} or None if model not available
    """
    models = load_models()
    
    if models is None or models.rf_model is None:
        logger.warning("Random Forest model not available for crime type prediction")
        return None
    
    try:
        # Encode district
        district_encoded = prepare_district_encoding(district, models.district_encoder)
        
        # Build feature vector [hour, day_of_week, month, lat, lng, district_encoded]
        features = np.array([[hour, day_of_week, month, lat, lng, district_encoded]])
        
        # Get prediction and probabilities
        prediction = models.rf_model.predict(features)[0]
        probabilities = models.rf_model.predict_proba(features)[0]
        
        # Get predicted type name
        predicted_type = inverse_transform_prediction(prediction, models.label_encoder)
        
        # Get confidence (max probability)
        confidence = float(max(probabilities))
        
        return {
            'predicted_type': predicted_type,
            'confidence': confidence
        }
        
    except Exception as e:
        logger.error(f"Error in crime type prediction: {e}")
        return None


def predict_crime_count(district, date_range_days):
    """
    Predict crime count for a district over a date range.
    
    Args:
        district (str): District name
        date_range_days (int): Number of days to forecast
    
    Returns:
        dict: {predicted_count: float, prediction_dates: list} or None if model not available
    """
    models = load_models()
    
    if models is None or models.lr_model is None:
        logger.warning("Linear Regression model not available for crime count prediction")
        return None
    
    try:
        # Get district encoding
        district_encoded = prepare_district_encoding(district, models.district_encoder)
        
        # Generate predictions for each day in range
        predictions = []
        dates = []
        base_date = datetime.now()
        
        for i in range(min(date_range_days, 30)):  # Cap at 30 days
            future_date = base_date + timedelta(days=i)
            
            # Features: [district_encoded, day_of_week, month, day_of_month]
            features = np.array([[
                district_encoded,
                future_date.weekday(),
                future_date.month,
                future_date.day
            ]])
            
            pred = models.lr_model.predict(features)[0]
            # Ensure non-negative
            pred = max(0, pred)
            predictions.append(pred)
            dates.append(future_date.strftime('%Y-%m-%d'))
        
        return {
            'predicted_count': predictions,
            'prediction_dates': dates
        }
        
    except Exception as e:
        logger.error(f"Error in crime count prediction: {e}")
        return None


def predict_lstm_forecast(historical_counts):
    """
    Forecast future crime counts using LSTM model.
    Uses 30 days of historical data to predict next 7 days.
    
    Args:
        historical_counts (list or np.array): Array of daily crime counts (at least 30 values)
    
    Returns:
        dict: {forecast: list, dates: list} or None if model not available
    """
    models = load_models()
    
    if models is None or models.lstm_model is None or models.scaler is None:
        logger.warning("LSTM model not available for forecasting")
        return None
    
    if not TF_AVAILABLE:
        logger.warning("TensorFlow not available")
        return None
    
    try:
        # Ensure we have at least 30 days of data
        if len(historical_counts) < 30:
            logger.warning(f"Insufficient historical data: {len(historical_counts)} days, need at least 30")
            return None
        
        # Take last 30 days
        data = np.array(historical_counts[-30:]).reshape(-1, 1)
        
        # Scale data
        scaled_data = models.scaler.transform(data)
        
        # Reshape for LSTM: [samples, timesteps, features]
        X = scaled_data.reshape(1, 30, 1)
        
        # Predict next 7 days
        forecast_scaled = models.lstm_model.predict(X)
        
        # Inverse transform
        forecast = models.scaler.inverse_transform(forecast_scaled.reshape(-1, 1)).flatten()
        
        # Ensure non-negative values
        forecast = np.maximum(forecast, 0)
        
        # Generate dates for forecast period
        base_date = datetime.now()
        forecast_dates = [
            (base_date + timedelta(days=i+1)).strftime('%Y-%m-%d')
            for i in range(7)
        ]
        
        return {
            'forecast': forecast.tolist(),
            'dates': forecast_dates
        }
        
    except Exception as e:
        logger.error(f"Error in LSTM forecast: {e}")
        return None


def get_model_info():
    """
    Get information about loaded models.
    
    Returns:
        dict: Information about available models and their status
    """
    models = load_models()
    
    if models is None:
        return {
            'loaded': False,
            'models': {}
        }
    
    info = {
        'loaded': True,
        'models': {
            'random_forest': {
                'available': models.rf_model is not None,
                'type': 'classification',
                'purpose': 'Crime type prediction'
            },
            'linear_regression': {
                'available': models.lr_model is not None,
                'type': 'regression',
                'purpose': 'Daily crime count prediction'
            },
            'lstm': {
                'available': models.lstm_model is not None,
                'type': 'time-series',
                'purpose': '7-day crime forecast'
            }
        }
    }
    
    return info