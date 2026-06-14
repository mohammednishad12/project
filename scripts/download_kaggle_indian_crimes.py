#!/usr/bin/env python3
"""
Kaggle Dataset Downloader for Indian Crimes Dataset

Downloads the sudhanvahg/indian-crimes-dataset from Kaggle,
unzips it, and lists the CSV files in the data directory.
"""

import subprocess
import os
import zipfile

# Dataset configuration
DATASET_SLUG = 'sudhanvahg/indian-crimes-dataset'
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

def download_and_extract():
    """Download and extract the Kaggle dataset."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    print(f"Downloading Kaggle dataset: {DATASET_SLUG}")
    print(f"Destination: {DOWNLOAD_DIR}")

    # Download using Kaggle CLI
    result = subprocess.run(
        ['kaggle', 'datasets', 'download', '-d', DATASET_SLUG, '-p', DOWNLOAD_DIR],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error downloading dataset: {result.stderr}")
        raise RuntimeError(f"Kaggle download failed: {result.stderr}")

    print("Download complete. Extracting...")

    # Find and extract the zip file
    zip_files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.zip')]
    if not zip_files:
        print("Warning: No zip file found after download.")
        return

    zip_path = os.path.join(DOWNLOAD_DIR, zip_files[0])
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(DOWNLOAD_DIR)

    # Remove the zip file after extraction
    os.remove(zip_path)

    print("Downloaded and extracted Kaggle dataset successfully!")
    print("\nFiles in data/:")
    for f in os.listdir(DOWNLOAD_DIR):
        filepath = os.path.join(DOWNLOAD_DIR, f)
        size = os.path.getsize(filepath) / 1024  # KB
        print(f"  - {f} ({size:.1f} KB)")

    # List CSV files specifically
    csv_files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.csv')]
    if csv_files:
        print(f"\nCSV files found: {csv_files}")
    else:
        print("\nNo CSV files found in data/ directory.")

if __name__ == '__main__':
    download_and_extract()