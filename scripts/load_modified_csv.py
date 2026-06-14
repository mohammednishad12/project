#!/usr/bin/env python3
"""
Load crime_dataset_modified.csv (or any CSV) into the database.
Convenience wrapper around ingest_data.py.
"""

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from app.models.crime import Crime
from scripts import ingest_data
from scripts import train_models


def truncate_crimes():
    """Delete all existing crime records."""
    app = create_app()
    with app.app_context():
        count = Crime.query.count()
        Crime.query.delete()
        db.session.commit()
        print(f"Truncated {count} existing crime records.")


def main():
    parser = argparse.ArgumentParser(
        description="Load crime_dataset_modified.csv into the database."
    )
    parser.add_argument(
        '--file', '-f',
        default='data/crime_dataset_modified.csv',
        help='Path to CSV file (default: data/crime_dataset_modified.csv)'
    )
    parser.add_argument(
        '--replace', action='store_true',
        help='Truncate existing data before loading (default: append)'
    )
    
    args = parser.parse_args()
    
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = os.path.join(PROJECT_ROOT, file_path)
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        print("Place your CSV file at data/crime_dataset_modified.csv or use --file")
        sys.exit(1)
    
    if args.replace:
        truncate_crimes()
    
    # Load and ingest
    df = ingest_data.load_csv(file_path)
    df_cleaned = ingest_data.clean_data(df)
    df_engineered = ingest_data.feature_engineer(df_cleaned)
    inserted = ingest_data.save_to_db(df_engineered)
    
    print(f"\n{'='*60}")
    print("INGESTION SUMMARY")
    print(f"{'='*60}")
    print(f"File: {file_path}")
    print(f"Records loaded: {len(df)}")
    print(f"Records cleaned: {len(df_cleaned)}")
    print(f"Records inserted: {inserted}")
    print(f"Mode: {'replace' if args.replace else 'append'}")
    print(f"{'='*60}\n")
    
    # Retrain models
    print("Retraining ML models...")
    train_models.main()
    print("Done!")


if __name__ == '__main__':
    main()