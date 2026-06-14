#!/usr/bin/env python3
"""
Data Ingestion CLI Script

Loads CSV or JSON crime data, cleans, feature-engineers, and inserts into database.
"""

import argparse
import csv
import json
import sys
import os
from datetime import datetime

import pandas as pd

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from app.models.crime import Crime


def load_csv(file_path):
    """Load a CSV file into a pandas DataFrame."""
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        print(f"Loaded {len(df)} records from CSV: {file_path}")
        return df
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='latin-1')
        print(f"Loaded {len(df)} records from CSV (latin-1 encoding): {file_path}")
        return df
    except Exception as e:
        print(f"Error loading CSV: {e}")
        raise


def load_json(file_path):
    """Load a JSON file into a pandas DataFrame."""
    try:
        # Try to handle both JSON arrays and JSON Lines format
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if content.startswith('['):
            df = pd.read_json(file_path, encoding='utf-8')
        else:
            # JSON Lines format
            records = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
            df = pd.DataFrame(records)
        
        print(f"Loaded {len(df)} records from JSON: {file_path}")
        return df
    except Exception as e:
        print(f"Error loading JSON: {e}")
        raise


def parse_date(date_str):
    """
    Parse a date string into a datetime object.
    Handles common formats: YYYY-MM-DD, MM/DD/YYYY, DD-MM-YYYY, datetime strings.
    Returns a datetime.date object or None if parsing fails.
    """
    if pd.isna(date_str):
        return None
    
    date_str = str(date_str).strip()
    
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y/%m/%d',
        '%m-%d-%Y',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%m/%d/%Y %I:%M:%S %p',
        '%d/%m/%Y %H:%M:%S',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date()
        except ValueError:
            continue
    
    # Try pandas parser as fallback
    try:
        return pd.to_datetime(date_str).date()
    except Exception:
        return None


def parse_time(time_str):
    """
    Parse a time string into a datetime.time object.
    Returns a datetime.time object or None if parsing fails.
    """
    if pd.isna(time_str):
        return None
    
    time_str = str(time_str).strip()
    
    formats = [
        '%H:%M:%S',
        '%H:%M',
        '%I:%M:%S %p',
        '%I:%M %p',
        '%H:%M:%S.%f',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.time()
        except ValueError:
            continue
    
    # Try pandas parser as fallback
    try:
        return pd.to_datetime(time_str).time()
    except Exception:
        return None


def clean_data(df):
    """
    Clean the DataFrame:
    - Standardize column names
    - Drop duplicate rows
    - Drop columns with >30% missing values
    - For remaining columns with missing values: numeric -> median, categorical -> mode
    - Standardize date columns to ISO 8601
    - Extract features: day_of_week, month, hour_of_day
    - Normalize latitude/longitude to float
    - Strip whitespace from string columns
    - Lowercase crime type for consistency
    
    Returns cleaned DataFrame and cleaning stats.
    """
    # Standardize column names first
    df = standardize_column_names(df)
    
    initial_count = len(df)
    
    # Drop duplicate rows
    df = df.drop_duplicates()
    duplicates_dropped = initial_count - len(df)
    
    # Calculate missing value percentages
    missing_pct = df.isnull().sum() / len(df)
    
    # Drop columns with >30% missing values
    cols_to_drop = missing_pct[missing_pct > 0.30].index.tolist()
    df = df.drop(columns=cols_to_drop)
    
    if cols_to_drop:
        print(f"Dropped columns with >30% missing: {cols_to_drop}")
    
    # Track imputation count
    total_imputed = 0
    
    # For remaining columns, impute missing values
    for col in df.columns:
        if df[col].isnull().any():
            if pd.api.types.is_numeric_dtype(df[col]):
                # Numeric: use median
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
                imputed_count = df[col].isnull().sum()  # This won't change after fillna
                total_imputed += df[col].isnull().sum() - imputed_count
            else:
                # Categorical: use mode
                mode_val = df[col].mode()
                if len(mode_val) > 0:
                    df[col] = df[col].fillna(mode_val[0])
                else:
                    df[col] = df[col].fillna('UNKNOWN')
    
    # Strip whitespace from string columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    
    return df


def standardize_column_names(df):
    """
    Standardize column names to match database schema.
    Handles common variations: latitude/lat, longitude/lng/lon, etc.
    """
    column_mapping = {}
    
    for col in df.columns:
        col_lower = col.lower().strip().replace(' ', '_')
        
        # Date variations
        if col_lower in ['date', 'crime_date', 'dt', 'incident_date', 'occurred_date']:
            column_mapping[col] = 'date'
        # Time variations
        elif col_lower in ['time', 'hour', 'incident_time', 'occurred_time', 'crime_time']:
            column_mapping[col] = 'time'
        # Latitude variations
        elif col_lower in ['latitude', 'lat', 'y']:
            column_mapping[col] = 'latitude'
        # Longitude variations
        elif col_lower in ['longitude', 'lng', 'lon', 'long', 'x']:
            column_mapping[col] = 'longitude'
        # Crime type variations
        elif col_lower in ['crime_type', 'primary_type', 'type', 'offense_type', 'crime_category']:
            column_mapping[col] = 'type'
        # District variations
        elif col_lower in ['district', 'area', 'community_area', 'ward', 'beat']:
            column_mapping[col] = 'district'
        # Description variations
        elif col_lower in ['description', 'desc', 'offense_description', 'crime_description']:
            column_mapping[col] = 'description'
        # Address variations
        elif col_lower in ['address', 'block', 'location', 'street_address', 'street']:
            column_mapping[col] = 'address'
    
    # Apply mapping (only rename if different)
    df = df.rename(columns=column_mapping)
    
    return df


def feature_engineer(df):
    """
    Add computed features to the DataFrame:
    - day_of_week (0=Monday, 6=Sunday)
    - month (1-12)
    - hour_of_day (0-23)
    - lat/lng from latitude/longitude (ensuring float type)
    """
    date_col = None
    time_col = None
    
    # Find date column
    for col in ['date', 'incident_date', 'occurred_date', 'crime_date']:
        if col in df.columns:
            date_col = col
            break
    
    # Find time column
    for col in ['time', 'hour', 'incident_time', 'occurred_time', 'crime_time']:
        if col in df.columns:
            time_col = col
            break
    
    # Extract day_of_week from date
    if date_col:
        df['parsed_date'] = df[date_col].apply(parse_date)
        df['day_of_week'] = df['parsed_date'].apply(
            lambda x: x.weekday() if x else None
        )
        df['month'] = df['parsed_date'].apply(
            lambda x: x.month if x else None
        )
        df['date_final'] = df['parsed_date']
    
    # Extract hour_of_day from time
    if time_col:
        df['parsed_time'] = df[time_col].apply(parse_time)
        df['hour_of_day'] = df['parsed_time'].apply(
            lambda x: x.hour if x else None
        )
    
    # Handle latitude/longitude ensuring float type
    if 'latitude' in df.columns:
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    
    if 'longitude' in df.columns:
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # Standardize case of type column
    if 'type' in df.columns:
        df['type'] = df['type'].apply(
            lambda x: x.lower().strip() if isinstance(x, str) else x
        )
    
    return df


def get_column_value(df, preferred_names, row_index=0):
    """Get the first matching column value from a list of preferred names."""
    for name in preferred_names:
        if name in df.columns:
            val = df.loc[row_index, name]
            if pd.notna(val):
                return val
    return None


def map_dataframe_to_crimes(df):
    """Map DataFrame columns to Crime model fields."""
    crimes = []
    
    # Determine column mappings once
    date_col = None
    for col in ['date', 'incident_date', 'occurred_date', 'crime_date']:
        if col in df.columns:
            date_col = col
            break
    
    time_col = None
    for col in ['time', 'hour', 'incident_time', 'occurred_time', 'crime_time']:
        if col in df.columns:
            time_col = col
            break
    
    type_col = None
    for col in ['type', 'crime_type', 'primary_type', 'offense_type', 'crime_category']:
        if col in df.columns:
            type_col = col
            break
    
    desc_col = None
    for col in ['description', 'desc', 'offense_description']:
        if col in df.columns:
            desc_col = col
            break
    
    lat_col = None
    for col in ['latitude', 'lat']:
        if col in df.columns:
            lat_col = col
            break
    
    lng_col = None
    for col in ['longitude', 'lng', 'lon', 'long']:
        if col in df.columns:
            lng_col = col
            break
    
    district_col = None
    for col in ['district', 'area', 'community_area', 'ward', 'beat']:
        if col in df.columns:
            district_col = col
            break
    
    address_col = None
    for col in ['address', 'block', 'location', 'street_address', 'street']:
        if col in df.columns:
            address_col = col
            break
    
    for idx in range(len(df)):
        # Use .iloc for positional access to avoid index gaps after deduplication
        row = df.iloc[idx]
        crime_date = None
        if date_col:
            crime_date = parse_date(row[date_col])
        
        crime_time = None
        if time_col:
            crime_time = parse_time(row[time_col])
        
        crime_type = None
        if type_col:
            val = row[type_col]
            if isinstance(val, str):
                crime_type = val.lower().strip()
            elif pd.notna(val):
                crime_type = str(val)
        
        if not crime_type:
            continue  # Skip rows without crime type
        
        description = None
        if desc_col:
            val = row[desc_col]
            if isinstance(val, str):
                description = val.strip()
            elif pd.notna(val):
                description = str(val)
        
        latitude = None
        if lat_col:
            val = row[lat_col]
            try:
                latitude = float(val) if pd.notna(val) else None
            except (ValueError, TypeError):
                latitude = None
        
        longitude = None
        if lng_col:
            val = row[lng_col]
            try:
                longitude = float(val) if pd.notna(val) else None
            except (ValueError, TypeError):
                longitude = None
        
        district = None
        if district_col:
            val = row[district_col]
            if isinstance(val, str):
                district = val.strip()
            elif pd.notna(val):
                district = str(val)
        
        address = None
        if address_col:
            val = row[address_col]
            if isinstance(val, str):
                address = val.strip()
            elif pd.notna(val):
                address = str(val)
        
        crimes.append(Crime(
            date=crime_date,
            time=crime_time,
            type=crime_type,
            description=description,
            latitude=latitude,
            longitude=longitude,
            district=district,
            address=address
        ))
    
    return crimes


def save_to_db(df):
    """
    Insert cleaned DataFrame into the Crime database model.
    Uses bulk insert for performance.
    """
    # Ensure columns are standardized
    df = standardize_column_names(df)
    
    # Map DataFrame to Crime objects
    crimes = map_dataframe_to_crimes(df)
    
    if not crimes:
        print("No valid crime records to insert.")
        return 0
    
    # Bulk insert
    db.session.bulk_save_objects(crimes)
    db.session.commit()
    
    print(f"Inserted {len(crimes)} records into database.")
    return len(crimes)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Ingest crime data from CSV or JSON files into the database.'
    )
    parser.add_argument(
        '--file', '-f',
        required=True,
        help='Path to the CSV or JSON file to ingest'
    )
    parser.add_argument(
        '--format',
        choices=['csv', 'json', 'auto'],
        default='auto',
        help='File format (auto-detect from extension if not specified)'
    )
    
    args = parser.parse_args()
    file_path = args.file
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    # Auto-detect format from extension
    if args.format == 'auto':
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.csv', '.tsv']:
            args.format = 'csv'
        elif ext in ['.json', '.jsonl']:
            args.format = 'json'
        else:
            print(f"Error: Cannot auto-detect format from extension '{ext}'. Please specify --format.")
            sys.exit(1)
    
    # Load data
    try:
        if args.format == 'csv':
            df = load_csv(file_path)
        else:
            df = load_json(file_path)
    except Exception as e:
        print(f"Failed to load data: {e}")
        sys.exit(1)
    
    # Clean data
    print(f"Loaded {len(df)} records")
    initial_count = len(df)
    df_cleaned = clean_data(df)
    duplicates_dropped = initial_count - len(df_cleaned)
    print(f"Cleaned: dropped {duplicates_dropped} duplicates")
    
    # Feature engineering
    df_engineered = feature_engineer(df_cleaned)
    print(f"Feature engineering complete")
    
    # Save to database
    app = create_app()
    with app.app_context():
        # Check if table exists, create if not
        db.create_all()
        
        inserted_count = save_to_db(df_engineered)
        print(f"Successfully ingested {inserted_count} crime records into the database.")


if __name__ == '__main__':
    main()