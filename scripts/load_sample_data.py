#!/usr/bin/env python3
"""
Sample Dataset Loader

Downloads Chicago Crime sample data or generates synthetic data if offline.
Saves raw data and ingests it into the database.
"""

import os
import sys
import random
import json
from datetime import datetime, timedelta

import pandas as pd
import requests

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.ingest_data import load_csv, load_json, clean_data, feature_engineer, save_to_db


# Chicago Crime Dataset API endpoint
CHICAGO_CRIME_API = "https://data.cityofchicago.org/resource/ijzp-q8t2.json"
API_LIMIT = 1000

# Synthetic data configuration
CRIME_TYPES = [
    'THEFT', 'BATTERY', 'CRIMINAL DAMAGE', 'NARCOTICS', 'ASSAULT',
    'ROBBERY', 'MOTOR VEHICLE THEFT', 'BURGLARY', 'DECEPTIVE PRACTICE',
    'CRIMINAL TRESPASS', 'WEAPONS VIOLATION', 'OFFENSE INVOLVING CHILDREN',
    'SEX OFFENSE', 'ARSON', 'KIDNAPPING', 'HOMICIDE', 'INTIMIDATION'
]

DISTRICTS = [
    'Central', 'Wentworth', 'Southwest', 'Bureau of Asset Management', 'Shakespeare',
    'Perintendent', 'Englewood', 'Chicago', 'Near West', 'North', 'Northeast',
    'Town Hall', 'Lincoln', 'Foster', 'Evanston', 'Rogers Park', 'Morgan Park',
    'Grand Central', 'Randall', 'Shakespeare', 'Pullman', 'Oakland', 'Lincoln Square'
]

DESCRIPTIONS = [
    'STREET', 'SIDEWALK', 'APARTMENT', 'RESIDENCE', 'PARKING LOT',
    'SCHOOL', 'PUBLIC BUILDING', 'COMMERCIAL', 'RETAIL STORE', 'RESTAURANT',
    'BAR OR TAVERN', 'HOTEL', 'MOTEL', 'VEHICLE NONRESIDENTIAL', 'ALLEY',
    'HALLWAY', 'Lobby', 'YARD', 'GARAGE', 'DRIVEWAY'
]

# Chicago bounds
CHICAGO_LAT_MIN = 41.65
CHICAGO_LAT_MAX = 42.02
CHICAGO_LNG_MIN = -87.94
CHICAGO_LNG_MAX = -87.52


def download_chicago_data(limit=API_LIMIT):
    """Download sample crime data from Chicago open data portal."""
    print(f"Attempting to download {limit} records from Chicago Crime API...")
    
    params = {
        '$limit': limit,
        '$order': 'date DESC'
    }
    
    try:
        response = requests.get(CHICAGO_CRIME_API, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data:
            print(f"Successfully downloaded {len(data)} records from Chicago API")
            
            # Convert to DataFrame (Chicago API returns array of objects)
            df = pd.DataFrame(data)
            
            # Standardize column names for Chicago data
            column_mapping = {
                'primary_type': 'type',
                'case_number': 'case_number',
                'date': 'date',
                'block': 'address',
                'description': 'description',
                'latitude': 'latitude',
                'longitude': 'longitude',
                'district': 'district',
                'community_area': 'area',
                'year': 'year',
                'updated_on': 'updated_on'
            }
            
            # Keep only relevant columns
            cols_to_keep = ['date', 'type', 'description', 'latitude', 'longitude', 'district', 'address']
            for col in cols_to_keep:
                if col in df.columns:
                    continue
                # Try alternate mappings
                if col == 'type' and 'primary_type' in df.columns:
                    df['type'] = df['primary_type']
                elif col == 'address' and 'block' in df.columns:
                    df['address'] = df['block']
            
            df = df[[c for c in cols_to_keep if c in df.columns]]
            
            return df, True
        else:
            print("API returned empty data")
            return None, False
            
    except requests.exceptions.Timeout:
        print("API request timed out")
        return None, False
    except requests.exceptions.ConnectionError:
        print("Could not connect to Chicago API (offline?)")
        return None, False
    except requests.exceptions.HTTPError as e:
        print(f"API HTTP error: {e}")
        return None, False
    except Exception as e:
        print(f"Unexpected error downloading data: {e}")
        return None, False


def generate_synthetic_data(num_records=500):
    """Generate realistic synthetic crime data when offline."""
    print(f"Generating {num_records} synthetic crime records...")
    
    # Generate dates within last 2 years
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # ~2 years
    
    records = []
    for i in range(num_records):
        # Random date
        random_days = random.randint(0, 730)
        crime_date = start_date + timedelta(days=random_days)
        
        # Random time
        random_seconds = random.randint(0, 86400)
        crime_time = datetime.min + timedelta(seconds=random_seconds)
        
        # Random location in Chicago area
        lat = random.uniform(CHICAGO_LAT_MIN, CHICAGO_LAT_MAX)
        lng = random.uniform(CHICAGO_LNG_MIN, CHICAGO_LNG_MAX)
        
        record = {
            'date': crime_date.strftime('%Y-%m-%d %H:%M:%S'),
            'type': random.choice(CRIME_TYPES),
            'description': random.choice(DESCRIPTIONS),
            'latitude': round(lat, 6),
            'longitude': round(lng, 6),
            'district': random.choice(DISTRICTS),
            'address': f"{random.randint(100, 9900)} {random.choice(['N', 'S', 'E', 'W'])} {random.choice(['Michigan', 'State', 'Clark', 'LaSalle', 'Halsted', 'Western', 'Pulaski', 'Central', 'Cicero'])} {random.choice(['St', 'Ave', 'Blvd', 'Rd'])}"
        }
        records.append(record)
    
    df = pd.DataFrame(records)
    print(f"Generated {len(df)} synthetic records")
    return df


def save_raw_data(df, output_path):
    """Save raw DataFrame to CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved raw data to: {output_path}")


def main():
    """Main entry point for sample data loading."""
    print("=" * 60)
    print("Crime Data Sample Loader")
    print("=" * 60)
    
    # Determine output paths
    data_dir = os.path.join(PROJECT_ROOT, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    raw_data_path = os.path.join(data_dir, 'sample_crimes.csv')
    
    # Try to download real data, fall back to synthetic
    df = None
    data_source = None
    
    print("\n[1/3] Fetching sample data...")
    df, downloaded = download_chicago_data(API_LIMIT)
    
    if downloaded and df is not None:
        data_source = "Chicago Open Data Portal"
    else:
        print("\nFalling back to synthetic data generation...")
        df = generate_synthetic_data(500)
        data_source = "Synthetic (offline)"
    
    # Save raw data
    print(f"\n[2/3] Saving raw data...")
    save_raw_data(df, raw_data_path)
    
    # Process and ingest data
    print(f"\n[3/3] Processing and ingesting data...")
    print(f"Source: {data_source}")
    print(f"Records loaded: {len(df)}")
    
    # Clean data
    initial_count = len(df)
    df_cleaned = clean_data(df)
    duplicates_dropped = initial_count - len(df_cleaned)
    print(f"Cleaned: dropped {duplicates_dropped} duplicates")
    
    # Feature engineering
    df_engineered = feature_engineer(df_cleaned)
    
    # Save to database
    from app import create_app, db
    app = create_app()
    
    with app.app_context():
        db.create_all()
        inserted_count = save_to_db(df_engineered)
    
    # Summary
    print("\n" + "=" * 60)
    print("LOAD SUMMARY")
    print("=" * 60)
    print(f"Source:            {data_source}")
    print(f"Total records:     {len(df)}")
    print(f"Duplicates dropped: {duplicates_dropped}")
    print(f"Values imputed:    {imputed_count}")
    print(f"Records inserted:  {inserted_count}")
    print(f"Raw data saved:    {raw_data_path}")
    print("=" * 60)
    
    if data_source == "Synthetic (offline)":
        print("\nNOTE: Data was generated synthetically because the Chicago API")
        print("was unreachable. For real data, ensure internet connectivity.")
    
    return inserted_count


if __name__ == '__main__':
    main()