"""
Prediction API Blueprint

This module provides the /api/predict endpoint for ML crime predictions.
Supports Random Forest (crime type), Linear Regression (crime count),
and LSTM (time-series forecast) models.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.ml.predict import load_models, predict_crime_type, predict_crime_count, predict_lstm_forecast
from app.models.prediction import Prediction
from app import db
import numpy as np
import logging

api_predict_bp = Blueprint('api_predict', __name__)
logger = logging.getLogger(__name__)

# Indian city center coordinates
CITY_COORDS = {
    'Delhi': {'lat': 28.61, 'lng': 77.21},
    'Mumbai': {'lat': 19.07, 'lng': 72.87},
    'Bangalore': {'lat': 12.97, 'lng': 77.59},
    'Chennai': {'lat': 13.08, 'lng': 80.27},
    'Kolkata': {'lat': 22.57, 'lng': 88.36},
    'Hyderabad': {'lat': 17.38, 'lng': 78.48},
    'Pune': {'lat': 18.52, 'lng': 73.85},
    'Ahmedabad': {'lat': 23.02, 'lng': 72.57},
    'Jaipur': {'lat': 26.91, 'lng': 75.79},
    'Lucknow': {'lat': 26.84, 'lng': 80.94},
    'Unknown': {'lat': 28.61, 'lng': 77.21},
}

# District/city names in priority order for hotspots
CITY_NAMES = list(CITY_COORDS.keys())[:-1]  # exclude Unknown


_CITY_COORDS_LIST = [(name, coords['lat'], coords['lng']) for name, coords in CITY_COORDS.items() if name != 'Unknown']


def get_district_from_location(lat, lng):
    """
    Determine the nearest Indian city from coordinates using Euclidean distance.

    Args:
        lat (float): Latitude
        lng (float): Longitude

    Returns:
        str: City/district name
    """
    nearest_city = 'Unknown'
    min_dist = float('inf')

    for city_name, city_lat, city_lng in _CITY_COORDS_LIST:
        dist = (lat - city_lat) ** 2 + (lng - city_lng) ** 2
        if dist < min_dist:
            min_dist = dist
            nearest_city = city_name

    return nearest_city


_cached_type_distribution = None
_cached_district_avg = None


def _get_crime_type_distribution():
    """Query DB for actual crime-type frequency distribution. Cached."""
    global _cached_type_distribution
    if _cached_type_distribution is not None:
        return _cached_type_distribution
    try:
        from app.models.crime import Crime
        results = db.session.query(Crime.type, db.func.count(Crime.id)).group_by(Crime.type).all()
        total = sum(c for _, c in results)
        _cached_type_distribution = {
            t: (count / total if total else 0)
            for t, count in results
        }
    except Exception as e:
        logger.warning(f'Failed to query crime type distribution: {e}')
        _cached_type_distribution = {
            'theft': 0.25, 'assault': 0.15, 'robbery': 0.10, 'burglary': 0.10,
            'fraud': 0.10, 'hit and run': 0.08, 'rape': 0.05, 'kidnapping': 0.05,
            'dowry death': 0.05, 'murder': 0.07
        }
    return _cached_type_distribution


def _get_district_avg_counts():
    """Query DB for average daily crime count per district. Cached."""
    global _cached_district_avg
    if _cached_district_avg is not None:
        return _cached_district_avg
    try:
        from app.models.crime import Crime
        results = db.session.query(
            Crime.district,
            db.func.count(Crime.id).label('count')
        ).filter(Crime.district.isnot(None)).group_by(Crime.district).all()
        # Estimate daily average using date range span
        date_span = db.session.query(
            db.func.max(Crime.date) - db.func.min(Crime.date)
        ).scalar()
        days = max(1, (date_span.days + 1) if date_span else 90)
        _cached_district_avg = {
            r.district: round(r.count / days, 1) for r in results
        }
    except Exception as e:
        logger.warning(f'Failed to query district averages: {e}')
        _cached_district_avg = {
            'Delhi': 45, 'Mumbai': 42, 'Bangalore': 38, 'Chennai': 35,
            'Kolkata': 32, 'Hyderabad': 40, 'Pune': 48, 'Ahmedabad': 50,
            'Jaipur': 52, 'Lucknow': 38
        }
    return _cached_district_avg


def generate_demo_crime_type(lat, lng, hour, day_of_week, month):
    """
    Generate a data-driven demo crime type prediction using actual DB frequencies.
    """
    distribution = _get_crime_type_distribution()
    types = list(distribution.keys())
    weights = list(distribution.values())

    # Slight time-of-day modifier: at night, shift weight toward violent crimes
    night_boost = {'robbery': 0.15, 'assault': 0.10, 'theft': -0.05, 'burglary': 0.05}
    if hour >= 22 or hour < 5:
        weights = [
            max(0.01, w + night_boost.get(t, 0))
            for t, w in zip(types, weights)
        ]

    total = sum(weights)
    weights = [w / total for w in weights]

    selected_idx = np.random.choice(len(types), p=weights)
    selected_type = types[selected_idx]
    confidence = min(0.95, weights[selected_idx] * 2 + 0.5)

    return {'type': selected_type, 'confidence': round(confidence, 2)}


def generate_demo_crime_count(district, days, historical_avg=None):
    """
    Generate data-driven demo crime count predictions using DB averages.
    """
    avgs = _get_district_avg_counts()
    base_count = avgs.get(district, historical_avg or 35)

    counts = []
    dates = []
    base_date = datetime.now()

    for i in range(min(days, 30)):
        future_date = base_date + timedelta(days=i)
        # Small variation (±15%) around historical average
        variation = np.random.uniform(0.85, 1.15)
        count = int(base_count * variation)
        counts.append(max(0, count))
        dates.append(future_date.strftime('%Y-%m-%d'))

    return {
        'predicted_count': counts[0] if len(counts) == 1 else counts,
        'prediction_dates': dates
    }


def generate_demo_lstm_forecast(historical_counts):
    """
    Generate data-driven demo forecast using historical rolling average.
    """
    if not historical_counts or len(historical_counts) == 0:
        historical_counts = [30] * 30

    avg_count = sum(historical_counts[-7:]) / min(7, len(historical_counts)) if historical_counts else 30

    forecast = []
    base_date = datetime.now()

    for i in range(7):
        variation = np.random.uniform(0.9, 1.1)
        count = int(avg_count * variation)
        forecast.append(max(0, count))

    dates = [(base_date + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(7)]

    return {'forecast': forecast, 'dates': dates}


def get_historical_daily_counts(days=30):
    """
    Query historical daily crime counts from the database.

    Args:
        days (int): Number of days of history to retrieve

    Returns:
        list: Daily crime counts for each day
    """
    try:
        from app.models.crime import Crime

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days+7)  # Extra days for buffer

        # Query crime counts grouped by date
        results = db.session.query(
            db.func.date(Crime.date).label('crime_date'),
            db.func.count(Crime.id).label('count')
        ).filter(
            Crime.date >= start_date,
            Crime.date <= end_date
        ).group_by(
            db.func.date(Crime.date)
        ).order_by(
            db.func.date(Crime.date).asc()
        ).all()

        # Build complete daily counts (fill missing days with average)
        date_counts = {r.crime_date: r.count for r in results}

        # Generate list for last N days
        counts = []
        for i in range(days, 0, -1):
            d = (end_date - timedelta(days=i)).date()
            if d in date_counts:
                counts.append(date_counts[d])
            else:
                # Estimate missing day
                if counts:
                    counts.append(int(sum(counts[-7:]) / min(7, len(counts[-7:]))) if len(counts) > 0 else 30)
                else:
                    counts.append(30)

        return counts

    except Exception as e:
        logger.warning(f"Could not retrieve historical data: {e}")
        return [30] * days


def get_top_districts_by_crime(limit=5):
    """
    Get top districts by historical crime count.

    Args:
        limit (int): Number of districts to return

    Returns:
        list: List of (district, count) tuples
    """
    try:
        from app.models.crime import Crime

        results = db.session.query(
            Crime.district,
            db.func.count(Crime.id).label('count')
        ).filter(
            Crime.district.isnot(None)
        ).group_by(
            Crime.district
        ).order_by(
            db.func.count(Crime.id).desc()
        ).limit(limit).all()

        return [(r.district, r.count) for r in results]

    except Exception as e:
        logger.warning(f"Could not get top districts: {e}")
        return []


@api_predict_bp.route('/api/predict', methods=['POST'])
def predict():
    """
    Main prediction endpoint.

    Expects JSON body:
    {
        "location": {"lat": float, "lng": float},
        "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    }

    Returns:
        JSON: {
            "predictions": {
                "crime_type": {"type": str, "confidence": float},
                "crime_count": {"predicted_count": int|list, "prediction_dates": list},
                "lstm_forecast": {"forecast": list, "dates": list}
            },
            "hotspots": [
                {"lat": float, "lng": float, "intensity": float, "predicted_type": str}
            ],
            "is_demo": bool
        }
    """
    # Validate request
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()

    # Validate required fields
    if 'location' not in data or 'date_range' not in data:
        return jsonify({'error': 'Missing required fields: location and date_range'}), 400

    location = data.get('location', {})
    date_range = data.get('date_range', {})

    lat = location.get('lat')
    lng = location.get('lng')
    start_date_str = date_range.get('start')
    end_date_str = date_range.get('end')

    if lat is None or lng is None:
        return jsonify({'error': 'Missing location coordinates'}), 400
    if not start_date_str or not end_date_str:
        return jsonify({'error': 'Missing date_range start or end'}), 400

    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        days = (end_date - start_date).days + 1
        if days <= 0:
            days = 1
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Determine district from location
    district = get_district_from_location(lat, lng)

    # Extract time features
    hour = 12  # Default to noon for general prediction
    day_of_week = start_date.weekday()
    month = start_date.month

    # Try to load models
    models = load_models()
    models_loaded = models is not None and any([models.rf_model, models.lr_model, models.lstm_model])

    is_demo = not models_loaded

    # Initialize predictions
    crime_type_prediction = None
    crime_count_prediction = None
    lstm_forecast = None

    # Get historical data for LSTM
    historical_counts = get_historical_daily_counts(30)

    # --- Crime Type Prediction (Random Forest) ---
    if models and models.rf_model:
        crime_type_prediction = predict_crime_type(lat, lng, hour, day_of_week, month, district)
        if crime_type_prediction:
            crime_type_prediction = {
                'type': crime_type_prediction.get('predicted_type', 'Unknown'),
                'confidence': crime_type_prediction.get('confidence', 0.5)
            }

    if not crime_type_prediction:
        # Generate demo prediction
        crime_type_prediction = generate_demo_crime_type(lat, lng, hour, day_of_week, month)

    # --- Crime Count Prediction (Linear Regression) ---
    if models and models.lr_model:
        count_result = predict_crime_count(district, days)
        if count_result:
            counts = count_result.get('predicted_count', [])
            dates = count_result.get('prediction_dates', [])
            # Calculate total if multiple days
            if isinstance(counts, list) and len(counts) > 0:
                crime_count_prediction = {
                    'predicted_count': sum(counts),
                    'prediction_dates': dates
                }
            else:
                crime_count_prediction = {
                    'predicted_count': int(counts) if counts else 0,
                    'prediction_dates': dates
                }

    if not crime_count_prediction:
        # Generate demo prediction
        crime_count_prediction = generate_demo_crime_count(district, days)

    # --- LSTM Forecast ---
    if models and models.lstm_model:
        lstm_result = predict_lstm_forecast(historical_counts)
        if lstm_result:
            lstm_forecast = lstm_result

    if not lstm_forecast:
        # Generate demo forecast
        lstm_forecast = generate_demo_lstm_forecast(historical_counts)

    # --- Save prediction to database ---
    try:
        prediction = Prediction(
            model_name='combined',
            location_lat=lat,
            location_lng=lng,
            predicted_type=crime_type_prediction.get('type') if isinstance(crime_type_prediction, dict) else None,
            confidence=crime_type_prediction.get('confidence') if isinstance(crime_type_prediction, dict) else None,
            prediction_date=start_date.date()
        )
        db.session.add(prediction)
        db.session.commit()
    except Exception as e:
        logger.warning(f"Could not save prediction to database: {e}")
        db.session.rollback()

    # --- Generate Hotspots ---
    hotspots = []
    top_districts = get_top_districts_by_crime(5)

    if not top_districts:
        # Use default city list with estimated counts
        avgs = _get_district_avg_counts()
        top_districts = [
            (c, int(avgs.get(c, 35) * 30))
            for c in CITY_NAMES[:5]
        ]

    for district_name, count in top_districts[:5]:
        coords = CITY_COORDS.get(district_name, CITY_COORDS['Unknown'])

        # Predict crime count for this district
        if models and models.lr_model:
            count_result = predict_crime_count(district_name, 1)
            if count_result:
                pred_count = count_result.get('predicted_count', 0)
                if isinstance(pred_count, list):
                    pred_count = sum(pred_count)
            else:
                pred_count = count / 30  # Rough daily average
        else:
            pred_count = count / 30

        # Generate hotspot crime type
        if models and models.rf_model:
            type_result = predict_crime_type(
                coords['lat'], coords['lng'],
                12, 3, datetime.now().month,
                district_name
            )
            predicted_type = type_result.get('predicted_type', 'Unknown') if type_result else 'Unknown'
        else:
            demo_type = generate_demo_crime_type(coords['lat'], coords['lng'], 12, 3, datetime.now().month)
            predicted_type = demo_type.get('type', 'Unknown')

        # Calculate intensity (0-1) based on predicted count
        max_count = 100  # Normalize to max 100 crimes/day
        intensity = min(1.0, pred_count / max_count)

        hotspots.append({
            'lat': coords['lat'],
            'lng': coords['lng'],
            'intensity': round(intensity, 2),
            'predicted_type': predicted_type,
            'district': district_name
        })

    # Sort hotspots by intensity
    hotspots.sort(key=lambda x: x['intensity'], reverse=True)

    # Build response
    response = {
        'predictions': {
            'crime_type': crime_type_prediction,
            'crime_count': crime_count_prediction,
            'lstm_forecast': lstm_forecast
        },
        'hotspots': hotspots,
        'is_demo': is_demo,
        'request': {
            'location': {'lat': lat, 'lng': lng},
            'date_range': {'start': start_date_str, 'end': end_date_str},
            'days': days,
            'district': district
        }
    }

    return jsonify(response), 200