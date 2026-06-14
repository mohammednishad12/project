#!/usr/bin/env python3
"""
Kaggle Indian Crimes Data Ingestion Script

Finds CSV files in data/, inspects columns, auto-maps to our schema,
and loads data into the database using existing ingest_data.py functions.
"""

import os
import sys
import json
import pandas as pd

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import existing ingest functions
from scripts.ingest_data import load_csv, clean_data, feature_engineer, save_to_db, standardize_column_names
from app import create_app, db
from app.models.crime import Crime

DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MAPPING_REPORT_PATH = os.path.join(PROJECT_ROOT, 'data', 'kaggle_column_mapping_report.json')


def find_csv_files():
    """Find all CSV files in the data directory."""
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {DATA_DIR}")
    return csv_files


def inspect_csv(filepath):
    """Inspect CSV columns and return summary."""
    df = load_csv(filepath)
    return df


def auto_map_columns(df):
    """
    Intelligently auto-map Kaggle CSV columns to our schema.
    Returns a mapping dict and saves a mapping report.
    
    Target schema: date, time, type, description, latitude, longitude, district, address
    """
    mapping = {}
    unmapped = []
    
    # Column name patterns to match
    patterns = {
        'date': ['date', 'Date', 'date_of_crime', 'crime_date', 'dt', 'year'],
        'time': ['time', 'Time', 'hour', 'Time_of_crime'],
        'type': ['type', 'Type', 'crime_type', 'Crime_Type', 'crime_head', 'ipc_section'],
        'description': ['description', 'Description', 'desc', 'details', 'crime_desc'],
        'latitude': ['latitude', 'lat', 'Lat', 'Latitude'],
        'longitude': ['longitude', 'lng', 'Lon', 'Longitude', 'long'],
        'district': ['district', 'District', 'city', 'City', 'state', 'State', 'area', 'location'],
        'address': ['address', 'Address', 'street', 'place']
    }
    
    for target_col, aliases in patterns.items():
        matched = False
        for col in df.columns:
            col_clean = col.lower().strip().replace(' ', '_')
            for alias in aliases:
                if col_clean == alias.lower().replace(' ', '_') or col_clean.startswith(alias.lower().replace(' ', '_')):
                    mapping[col] = target_col
                    matched = True
                    break
            if matched:
                break
        if not matched:
            unmapped.append(target_col)
    
    return mapping, unmapped


def print_inspection_summary(df):
    """Print clear summary of columns and sample rows."""
    print("\n" + "=" * 60)
    print("CSV INSPECTION SUMMARY")
    print("=" * 60)
    print(f"\nShape: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"\nColumn names and dtypes:")
    print("-" * 40)
    for col in df.columns:
        non_null = df[col].notna().sum()
        pct = (non_null / len(df)) * 100
        print(f"  {col}: {df[col].dtype} ({pct:.1f}% populated)")
    
    print(f"\nFirst 5 rows:")
    print("-" * 40)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(df.head().to_string())


def save_mapping_report(mapping, unmapped, df, csv_path):
    """Save mapping report to JSON file."""
    report = {
        'csv_file': csv_path,
        'mapping': mapping,
        'unmapped_fields': unmapped,
        'original_columns': list(df.columns),
        'target_schema': ['date', 'time', 'type', 'description', 'latitude', 'longitude', 'district', 'address']
    }
    with open(MAPPING_REPORT_PATH, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nMapping report saved to: {MAPPING_REPORT_PATH}")


def main():
    """Main ingestion entry point."""
    print("Kaggle Indian Crimes Data Ingestion")
    print("=" * 60)
    
    # Find CSV files
    csv_files = find_csv_files()
    print(f"\nFound {len(csv_files)} CSV file(s): {csv_files}")
    
    # Use the first/largest CSV (likely the main dataset)
    csv_path = os.path.join(DATA_DIR, csv_files[0])
    print(f"\nUsing: {csv_path}")
    
    # Inspect CSV
    df = inspect_csv(csv_path)
    print_inspection_summary(df)
    
    # Auto-map columns
    mapping, unmapped = auto_map_columns(df)
    print("\n" + "=" * 60)
    print("COLUMN MAPPING")
    print("=" * 60)
    print("\nDetected mappings:")
    for orig, target in mapping.items():
        print(f"  {orig} -> {target}")
    
    if unmapped:
        print(f"\nUnmapped fields (will use defaults/nulls): {unmapped}")
    
    # Save mapping report
    save_mapping_report(mapping, unmapped, df, csv_files[0])
    
    # Rename columns according to mapping
    df_mapped = df.rename(columns=mapping)
    
    # Clean data
    print("\n" + "=" * 60)
    print("DATA CLEANING")
    print("=" * 60)
    initial_count = len(df_mapped)
    df_cleaned = clean_data(df_mapped)
    duplicates_dropped = initial_count - len(df_cleaned)
    print(f"Cleaned: dropped {duplicates_dropped} duplicates")
    
    # Feature engineering
    df_engineered = feature_engineer(df_cleaned)
    print("Feature engineering complete")
    
    # Save to database
    print("\n" + "=" * 60)
    print("DATABASE INGESTION")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        db.create_all()
        
        # Truncate existing crimes table
        print("Truncating existing crimes table...")
        db.session.execute(db.text('DELETE FROM crimes'))
        db.session.commit()
        
        # Insert new data
        inserted_count = save_to_db(df_engineered)
        print(f"Successfully ingested {inserted_count} crime records.")
    
    # Trigger model retraining
    print("\n" + "=" * 60)
    print("MODEL RETRAINING")
    print("=" * 60)
    print("Retraining models after ingestion...")
    try:
        from scripts.train_models import main as train_models_main
        train_models_main()
        print("Model retraining complete!")
    except Exception as e:
        print(f"Warning: Model retraining failed: {e}")
        print("You may need to retrain models manually.")
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == '__main__':
    main()