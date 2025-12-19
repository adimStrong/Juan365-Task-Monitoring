"""Configuration for Streamlit File Upload Portal"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
BACKEND_DIR = PROJECT_ROOT / 'backend'

# Database
DATABASE_PATH = BACKEND_DIR / 'db.sqlite3'

# Media storage
MEDIA_ROOT = BACKEND_DIR / 'media'
ASSETS_DIR = MEDIA_ROOT / 'assets'

# File upload limits (in MB)
MAX_IMAGE_SIZE = 100
MAX_VIDEO_SIZE = 500
MAX_DOCUMENT_SIZE = 100
MAX_OTHER_SIZE = 100

# Supported file types
SUPPORTED_IMAGES = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
SUPPORTED_VIDEOS = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
SUPPORTED_DOCUMENTS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv']

# MIME type mappings
IMAGE_MIMES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/svg+xml']
VIDEO_MIMES = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/x-matroska']
DOCUMENT_MIMES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'text/csv'
]

# Ensure directories exist
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
