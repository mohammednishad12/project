#!/usr/bin/env python3
"""
Indian Crime Data Loader

Generates 10,000 synthetic Indian crime records and ingests them into the database.
Saves raw data to data/india_crimes.csv and uses existing ingest_data functions.
"""

import os
import sys
import random
from datetime import datetime, timedelta

import pandas as pd

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.ingest_data import clean_data, feature_engineer, save_to_db

# Crime type distribution (percentages)
CRIME_TYPES = {
    'theft': 25,
    'assault': 15,
    'robbery': 10,
    'burglary': 10,
    'fraud': 10,
    'hit and run': 8,
    'rape': 5,
    'kidnapping': 5,
    'dowry death': 5,
    'murder': 7
}

# Indian districts (cities)
DISTRICTS = [
    'delhi', 'mumbai', 'bangalore', 'chennai', 'kolkata',
    'hyderabad', 'pune', 'ahmedabad', 'jaipur', 'lucknow'
]

# Base coordinates for each city
CITY_COORDS = {
    'delhi': (28.61, 77.21),
    'mumbai': (19.07, 72.87),
    'bangalore': (12.97, 77.59),
    'chennai': (13.08, 80.27),
    'kolkata': (22.57, 88.36),
    'hyderabad': (17.38, 78.48),
    'pune': (18.52, 73.85),
    'ahmedabad': (23.02, 72.57),
    'jaipur': (26.91, 75.79),
    'lucknow': (26.84, 80.94)
}

# Location descriptions (20 items)
DESCRIPTIONS = [
    'main road', 'residential area', 'market', 'bus stand', 'railway station',
    'temple', 'mosque', 'hospital', 'school', 'office complex',
    'construction site', 'highway', 'village', 'mohalla', 'bazaar',
    'mall', 'park', 'bridge', 'slum area', 'industrial area'
]

# Street name components
STREET_PREFIXES = ['Main', 'Ring', 'MG', 'Nehru', 'Mahatma Gandhi', 'Station', 'Civil', 'Lal', 'Shah', 'Park']
STREET_SUFFIXES = ['Road', 'Street', 'Marg', 'Chowk', 'Nagar', 'Colony', 'Block', 'Lane', 'Circle', 'Cross']
STREET_NAMES = ['{p} {s}' for p in STREET_PREFIXES for s in STREET_SUFFIXES]

# Common Indian street numbers
STREET_NUMBERS = list(range(1, 501))


def generate_street_names():
    """Generate 20 unique street names per city."""
    random.shuffle(STREET_NAMES)
    return STREET_NAMES[:20]


def get_weighted_crime_type():
    """Return a crime type based on weighted distribution."""
    r = random.randint(1, 100)
    cumulative = 0
    for crime_type, percentage in CRIME_TYPES.items():
        cumulative += percentage
        if r <= cumulative:
            return crime_type
    return 'theft'  # fallback


def generate_indian_crime_data(num_records=10000, start_date='2026-01-01', end_date='2026-03-31'):
    """Generate synthetic Indian crime records."""
    print(f"Generating {num_records} synthetic Indian crime records...")

    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    date_range_days = (end - start).days + 1

    records = []
    city_street_names = {city: generate_street_names() for city in DISTRICTS}

    for i in range(num_records):
        # Random date within range
        random_days = random.randint(0, date_range_days - 1)
        crime_date = start + timedelta(days=random_days)

        # Random time
        random_hour = random.randint(0, 23)
        random_minute = random.randint(0, 59)
        crime_time = f"{random_hour:02d}:{random_minute:02d}:00"

        # Random district
        district = random.choice(DISTRICTS)

        # Get coordinates with ±0.05 random offset
        base_lat, base_lng = CITY_COORDS[district]
        lat = round(base_lat + random.uniform(-0.05, 0.05), 6)
        lng = round(base_lng + random.uniform(-0.05, 0.05), 6)

        # Crime type based on distribution
        crime_type = get_weighted_crime_type()

        # Description
        description = random.choice(DESCRIPTIONS)

        # Address: {street_number} {street_name}, {district}
        street_name = random.choice(city_street_names[district])
        street_number = random.choice(STREET_NUMBERS)
        address = f"{street_number} {street_name}, {district.capitalize()}"

        record = {
            'date': crime_date.strftime('%Y-%m-%d'),
            'time': crime_time,
            'type': crime_type,  # Already lowercase
            'description': description,
            'latitude': lat,
            'longitude': lng,
            'district': district.capitalize(),
            'address': address
        }
        records.append(record)

        # Progress indicator
        if (i + 1) % 2000 == 0:
            print(f"  Generated {i + 1} records...")

    df = pd.DataFrame(records)
    print(f"Generated {len(df)} records")
    return df


def save_raw_data(df, output_path):
    """Save raw DataFrame to CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")


def truncate_crimes_table():
    """Truncate the crimes table before loading new data."""
    from app import create_app, db
    from app.models.crime import Crime

    app = create_app()
    with app.app_context():
        count = Crime.query.delete()
        db.session.commit()
        print(f"Truncated {count} existing records from crimes table")
        return count


def main():
    """Main entry point for Indian data loading."""
    print("=" * 60)
    print("Indian Crime Data Loader")
    print("=" * 60)

    # Configuration
    num_records = 10000
    start_date = '2026-01-01'
    end_date = '2026-03-31'

    # Output paths
    data_dir = os.path.join(PROJECT_ROOT, 'data')
    os.makedirs(data_dir, exist_ok=True)
    raw_data_path = os.path.join(data_dir, 'india_crimes.csv')

    # Step 1: Truncate existing data
    print("\n[1/4] Truncating existing data...")
    truncate_crimes_table()

    # Step 2: Generate synthetic data
    print(f"\n[2/4] Generating {num_records} synthetic Indian crime records...")
    df = generate_indian_crime_data(num_records, start_date, end_date)

    # Step 3: Save raw data
    print(f"\n[3/4] Saving raw data...")
    save_raw_data(df, raw_data_path)
    print(f"Saved {len(df)} records")

    # Step 4: Clean and ingest data
    print(f"\n[4/4] Cleaning and ingesting data...")
    df_cleaned, duplicates_dropped, imputed_count = clean_data(df)
    print(f"Cleaned: dropped {duplicates_dropped} duplicates, imputed {imputed_count} values")

    df_engineered = feature_engineer(df_cleaned)

    from app import create_app, db
    app = create_app()
    with app.app_context():
        db.create_all()
        inserted_count = save_to_db(df_engineered)

    # Summary
    print("\n" + "=" * 60)
    print("LOAD SUMMARY")
    print("=" * 60)
    print(f"Date range:        {start_date} to {end_date} (90 days)")
    print(f"Total generated:   {len(df)}")
    print(f"Duplicates dropped: {duplicates_dropped}")
    print(f"Values imputed:    {imputed_count}")
    print(f"Records inserted:  {inserted_count}")
    print(f"Raw data saved:    {raw_data_path}")
    print("=" * 60)

    return inserted_count


if __name__ == '__main__':
    main()