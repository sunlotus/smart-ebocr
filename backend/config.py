# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

import os

APP_VERSION = "1.0.0"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'smart-ebocr.db')

SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# Flask session
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}

# Logging configuration
LOG_DIR = os.path.join(BASE_DIR, 'backend', 'logs')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')

# Shandong default pricing policy
DEFAULT_POLICY = {
    'name': '山东居民电价',
    'region': 'shandong',
    'tier1_rate': 0.5469,
    'tier1_limit': 2520,
    'tier2_rate': 0.5969,
    'tier2_limit': 4800,
    'tier3_rate': 0.8469,
    'peak_rate': 0.5769,
    'valley_rate': 0.3769,
    'heating_valley_rate': 0.3469,
    'sharp_rate': 0.6769,
    'flat_rate': 0.5469,
    'peak_hours': [{'start': '08:00', 'end': '22:00'}],
    'valley_hours': [{'start': '22:00', 'end': '06:00'}],
}
