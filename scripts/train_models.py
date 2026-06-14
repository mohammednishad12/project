#!/usr/bin/env python3
"""
Model Training Script

Trains and saves three ML models:
1. Random Forest Classifier - predict crime type
2. Linear Regression - predict daily crime count per district
3. LSTM - time-series forecasting of daily crime counts

Run from project root: python scripts/train_models.py
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import joblib

# ML imports
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_squared_error, r2_score

# TensorFlow/Keras - handle import errors gracefully
try:
    import tensorflow as tf
    tf.get_logger().setLevel('ERROR')
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("WARNING: TensorFlow not available. LSTM model will not be trained.")


def create_app_context():
    """Create Flask app context for database access."""
    from app import create_app, db
    app = create_app()
    return app, app.app_context()


def load_crime_data():
    """Load crime data from database."""
    from app.models.crime import Crime
    
    app, ctx = create_app_context()
    with ctx:
        crimes = Crime.query.all()
        
        if not crimes:
            print("WARNING: No crime data in database. Will use synthetic data.")
            return None
        
        # Convert to DataFrame
        data = []
        for crime in crimes:
            data.append({
                'id': crime.id,
                'date': crime.date,
                'time': crime.time,
                'type': crime.type,
                'description': crime.description,
                'latitude': crime.latitude,
                'longitude': crime.longitude,
                'district': crime.district,
                'address': crime.address
            })
        
        df = pd.DataFrame(data)
        print(f"Loaded {len(df)} crime records from database")
        return df


def generate_synthetic_training_data(num_records=1000):
    """Generate synthetic India data for training when database is empty."""
    print("Generating synthetic training data...")

    CRIME_TYPES = [
        'theft', 'assault', 'robbery', 'burglary', 'fraud',
        'hit and run', 'rape', 'kidnapping', 'dowry death', 'murder'
    ]

    DISTRICTS = [
        'Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata',
        'Hyderabad', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow'
    ]

    CITY_COORDS = {
        'Delhi': (28.61, 77.21), 'Mumbai': (19.07, 72.87),
        'Bangalore': (12.97, 77.59), 'Chennai': (13.08, 80.27),
        'Kolkata': (22.57, 88.36), 'Hyderabad': (17.38, 78.48),
        'Pune': (18.52, 73.85), 'Ahmedabad': (23.02, 72.57),
        'Jaipur': (26.91, 75.79), 'Lucknow': (26.84, 80.94)
    }

    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)

    data = []
    for i in range(num_records):
        random_days = random.randint(0, 730)
        crime_date = start_date + timedelta(days=random_days)
        district = random.choice(DISTRICTS)
        base_lat, base_lng = CITY_COORDS[district]

        data.append({
            'date': crime_date.date(),
            'time': crime_date.time(),
            'type': random.choice(CRIME_TYPES),
            'latitude': base_lat + random.uniform(-0.05, 0.05),
            'longitude': base_lng + random.uniform(-0.05, 0.05),
            'district': district
        })

    return pd.DataFrame(data)


def prepare_classification_features(df, district_encoder=None):
    """Prepare features for crime type classification."""
    df = df.copy()

    if 'time' in df.columns:
        if hasattr(df['time'].iloc[0] if len(df) > 0 else None, 'hour'):
            df['hour_of_day'] = df['time'].apply(lambda t: t.hour if t else None)
        elif df['time'].dtype != 'object':
            df['hour_of_day'] = pd.to_datetime(df['time'], format='%H:%M:%S').dt.hour
        else:
            df['hour_of_day'] = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce').dt.hour

    if 'date' in df.columns:
        if df['date'].dtype == 'object':
            df['parsed_date'] = pd.to_datetime(df['date'])
        else:
            df['parsed_date'] = pd.to_datetime(df['date'])
        df['day_of_week'] = df['parsed_date'].dt.dayofweek
        df['month'] = df['parsed_date'].dt.month

    # Encode district using provided encoder or fit new one
    if district_encoder is None:
        district_encoder = LabelEncoder()
        df['district_encoded'] = district_encoder.fit_transform(df['district'].fillna('Unknown'))
    else:
        df['district_encoded'] = district_encoder.transform(df['district'].fillna('Unknown'))

    # Feature matrix
    feature_cols = ['hour_of_day', 'day_of_week', 'month', 'latitude', 'longitude', 'district_encoded']

    df_clean = df.dropna(subset=feature_cols + ['type'])

    X = df_clean[feature_cols].values
    y = df_clean['type'].values

    return X, y, district_encoder


def prepare_regression_features(df, district_encoder=None):
    """Prepare features for daily crime count prediction."""
    df = df.copy()

    if 'date' in df.columns:
        if df['date'].dtype == 'object':
            df['parsed_date'] = pd.to_datetime(df['date'])
        else:
            df['parsed_date'] = pd.to_datetime(df['date'])

    daily_counts = df.groupby(['district', 'parsed_date']).size().reset_index(name='crime_count')

    if len(daily_counts) < 10:
        return None, None, None

    daily_counts['day_of_week'] = daily_counts['parsed_date'].dt.dayofweek
    daily_counts['month'] = daily_counts['parsed_date'].dt.month
    daily_counts['day_of_month'] = daily_counts['parsed_date'].dt.day

    if district_encoder is None:
        district_encoder = LabelEncoder()
        daily_counts['district_encoded'] = district_encoder.fit_transform(daily_counts['district'].fillna('Unknown'))
    else:
        daily_counts['district_encoded'] = district_encoder.transform(daily_counts['district'].fillna('Unknown'))

    feature_cols = ['district_encoded', 'day_of_week', 'month', 'day_of_month']

    X = daily_counts[feature_cols].values
    y = daily_counts['crime_count'].values

    return X, y, district_encoder


def prepare_lstm_data(df):
    """Prepare time-series data for LSTM forecasting."""
    if 'date' in df.columns:
        if df['date'].dtype == 'object':
            df['parsed_date'] = pd.to_datetime(df['date'])
        else:
            df['parsed_date'] = pd.to_datetime(df['date'])
    
    # Aggregate daily totals
    daily_totals = df.groupby('parsed_date').size().reset_index(name='crime_count')
    daily_totals = daily_totals.sort_values('parsed_date')
    
    if len(daily_totals) < 30:
        return None, None, None
    
    # Fill in missing dates with 0
    date_range = pd.date_range(
        start=daily_totals['parsed_date'].min(),
        end=daily_totals['parsed_date'].max(),
        freq='D'
    )
    daily_totals = daily_totals.set_index('parsed_date').reindex(date_range, fill_value=0)
    daily_totals = daily_totals.reset_index().rename(columns={'index': 'date'})
    
    crime_counts = daily_totals['crime_count'].values.reshape(-1, 1)
    
    return crime_counts, daily_totals['date'].values, daily_totals


def create_sequences(data, seq_length=30, forecast_length=7):
    """Create sequences for LSTM: seq_length input -> forecast_length output."""
    X, y = [], []
    for i in range(len(data) - seq_length - forecast_length + 1):
        X.append(data[i:i + seq_length])
        y.append(data[i + seq_length:i + seq_length + forecast_length])
    return np.array(X), np.array(y)


def train_random_forest(X, y):
    """Train Random Forest classifier for crime type prediction."""
    print("\n" + "=" * 50)
    print("Training Random Forest Classifier")
    print("=" * 50)
    
    # Encode target labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42
    )
    
    # Train model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=20,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))
    
    accuracy = (y_pred == y_test).mean()
    print(f"Accuracy: {accuracy:.4f}")
    
    # Save model and label encoder
    models_dir = os.path.join(PROJECT_ROOT, 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    joblib.dump(model, os.path.join(models_dir, 'crime_type_rf.pkl'))
    joblib.dump(label_encoder, os.path.join(models_dir, 'crime_type_label_encoder.pkl'))
    print(f"\nSaved: models/crime_type_rf.pkl")
    print(f"Saved: models/crime_type_label_encoder.pkl")
    
    return model, accuracy


def train_linear_regression(X, y):
    """Train Linear Regression for daily crime count prediction."""
    print("\n" + "=" * 50)
    print("Training Linear Regression Model")
    print("=" * 50)
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train model
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"\nMean Squared Error: {mse:.4f}")
    print(f"R² Score: {r2:.4f}")
    print(f"RMSE: {np.sqrt(mse):.4f}")
    
    # Save model
    models_dir = os.path.join(PROJECT_ROOT, 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    joblib.dump(model, os.path.join(models_dir, 'crime_count_lr.pkl'))
    print(f"\nSaved: models/crime_count_lr.pkl")
    
    return model, mse, r2


def train_lstm(crime_counts):
    """Train LSTM for time-series forecasting."""
    print("\n" + "=" * 50)
    print("Training LSTM Model")
    print("=" * 50)
    
    if not TF_AVAILABLE:
        print("SKIPPED: TensorFlow not available")
        return None, None
    
    # Normalize data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(crime_counts)
    
    # Create sequences
    seq_length = 30
    forecast_length = 7
    
    if len(scaled_data) < seq_length + forecast_length + 10:
        print(f"SKIPPED: Insufficient data ({len(scaled_data)} points, need {seq_length + forecast_length + 10})")
        return None, None
    
    X, y = create_sequences(scaled_data, seq_length, forecast_length)
    print(f"Sequence data shape: X={X.shape}, y={y.shape}")
    
    # Train/test split
    split_idx = int(len(X) * 0.9)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Build model
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(seq_length, 1)),
        LSTM(50, return_sequences=False),
        Dense(forecast_length)
    ])
    
    model.compile(optimizer='adam', loss='mse')
    model.summary()
    
    # Early stopping
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=5,
        restore_best_weights=True
    )
    
    # Train
    history = model.fit(
        X_train, y_train,
        epochs=20,
        batch_size=32,
        validation_split=0.1,
        callbacks=[early_stop],
        verbose=1
    )
    
    # Evaluate
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test.flatten(), y_pred.flatten())
    print(f"\nTest MSE: {mse:.6f}")
    
    # Save model and scaler
    models_dir = os.path.join(PROJECT_ROOT, 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    model.save(os.path.join(models_dir, 'crime_lstm.h5'))
    joblib.dump(scaler, os.path.join(models_dir, 'crime_scaler.pkl'))
    print(f"\nSaved: models/crime_lstm.h5")
    print(f"Saved: models/crime_scaler.pkl")
    
    return model, mse


def main():
    """Main training entry point."""
    print("=" * 60)
    print("Crime Prediction Model Training")
    print("=" * 60)
    
    # Create directories
    models_dir = os.path.join(PROJECT_ROOT, 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    # Load data from database
    df = load_crime_data()
    
    # If no data, use synthetic
    if df is None or len(df) < 100:
        print("\nWARNING: Insufficient data in database (< 100 records)")
        print("Training on synthetic data instead...")
        import random
        df = generate_synthetic_training_data(1000)
        
        # Save synthetic data indicator
        with open(os.path.join(models_dir, '.synthetic_training'), 'w') as f:
            f.write(f"Trained on synthetic data at {datetime.now()}\n")
            f.write(f"Records used: {len(df)}\n")
    else:
        # Remove indicator file if it exists
        synthetic_file = os.path.join(models_dir, '.synthetic_training')
        if os.path.exists(synthetic_file):
            os.remove(synthetic_file)
    
    # Create shared district encoder from all unique districts
    all_districts = df['district'].fillna('Unknown').unique().tolist()
    district_encoder = LabelEncoder()
    district_encoder.fit(all_districts)

    # Save district encoder immediately
    de_path = os.path.join(models_dir, 'district_encoder.pkl')
    joblib.dump(district_encoder, de_path)
    print(f"Saved: {de_path}")

    # Track overall results
    results = {}

    # 1. Train Random Forest
    try:
        X_cls, y_cls, _ = prepare_classification_features(df, district_encoder=district_encoder)

        if X_cls is not None and len(np.unique(y_cls)) > 1:
            model, accuracy = train_random_forest(X_cls, y_cls)
            results['random_forest'] = {'accuracy': accuracy}
        else:
            print("\nSKIPPED: Random Forest - insufficient class diversity")
            results['random_forest'] = {'accuracy': None, 'skipped': 'Single class or insufficient data'}
    except Exception as e:
        print(f"\nERROR in Random Forest training: {e}")
        results['random_forest'] = {'accuracy': None, 'error': str(e)}

    # 2. Train Linear Regression
    try:
        X_reg, y_reg, _ = prepare_regression_features(df, district_encoder=district_encoder)

        if X_reg is not None and len(X_reg) >= 10:
            model, mse, r2 = train_linear_regression(X_reg, y_reg)
            results['linear_regression'] = {'mse': mse, 'r2': r2}
        else:
            print("\nSKIPPED: Linear Regression - insufficient data for aggregation")
            results['linear_regression'] = {'mse': None, 'r2': None, 'skipped': 'Insufficient aggregated data'}
    except Exception as e:
        print(f"\nERROR in Linear Regression training: {e}")
        results['linear_regression'] = {'mse': None, 'r2': None, 'error': str(e)}
    
    # 3. Train LSTM
    try:
        crime_counts, dates, daily_df = prepare_lstm_data(df)
        
        if crime_counts is not None and len(crime_counts) >= 40:
            model, mse = train_lstm(crime_counts)
            results['lstm'] = {'mse': mse}
        else:
            print("\nSKIPPED: LSTM - need at least 40 days of data")
            results['lstm'] = {'mse': None, 'skipped': 'Insufficient time-series data'}
    except Exception as e:
        print(f"\nERROR in LSTM training: {e}")
        results['lstm'] = {'mse': None, 'error': str(e)}
    
    # Print summary
    print("\n" + "=" * 60)
    print("TRAINING SUMMARY")
    print("=" * 60)
    print(f"Data source: {'Synthetic' if os.path.exists(os.path.join(models_dir, '.synthetic_training')) else 'Database'}")
    print(f"Records used: {len(df)}")
    print()
    
    for model_name, metrics in results.items():
        print(f"{model_name.upper().replace('_', ' ')}:")
        if 'skipped' in metrics:
            print(f"  Status: SKIPPED - {metrics['skipped']}")
        elif 'error' in metrics:
            print(f"  Status: ERROR - {metrics['error']}")
        else:
            for metric, value in metrics.items():
                if value is not None:
                    print(f"  {metric}: {value:.4f}" if isinstance(value, float) else f"  {metric}: {value}")
    print("=" * 60)
    
    return results


if __name__ == '__main__':
    main()