#!/usr/bin/env python3
"""
Kaggle Authentication Setup Script

Prompts the user for Kaggle username and API key, then creates ~/.kaggle/kaggle.json.
"""

import json
import os

kaggle_dir = os.path.expanduser('~/.kaggle')
os.makedirs(kaggle_dir, exist_ok=True)

username = input('Enter your Kaggle username: ').strip()
api_key = input('Enter your Kaggle API key: ').strip()

with open(os.path.join(kaggle_dir, 'kaggle.json'), 'w') as f:
    json.dump({'username': username, 'key': api_key}, f)

os.chmod(os.path.join(kaggle_dir, 'kaggle.json'), 0o600)
print('Kaggle authentication configured successfully!')