"""File handling utilities"""
import os
import mimetypes
from pathlib import Path
from datetime import datetime

from config import (
    ASSETS_DIR, SUPPORTED_IMAGES, SUPPORTED_VIDEOS, SUPPORTED_DOCUMENTS,
    IMAGE_MIMES, VIDEO_MIMES, DOCUMENT_MIMES,
    MAX_IMAGE_SIZE, MAX_VIDEO_SIZE, MAX_DOCUMENT_SIZE, MAX_OTHER_SIZE
)

def get_file_type(filename, mime_type=None):
    """Determine file type from extension or MIME type"""
    ext = Path(filename).suffix.lower()

    if ext in SUPPORTED_IMAGES or (mime_type and mime_type in IMAGE_MIMES):
        return 'image'
    elif ext in SUPPORTED_VIDEOS or (mime_type and mime_type in VIDEO_MIMES):
        return 'video'
    elif ext in SUPPORTED_DOCUMENTS or (mime_type and mime_type in DOCUMENT_MIMES):
        return 'document'
    else:
        return 'other'

def get_max_size_mb(file_type):
    """Get maximum file size in MB for a file type"""
    sizes = {
        'image': MAX_IMAGE_SIZE,
        'video': MAX_VIDEO_SIZE,
        'document': MAX_DOCUMENT_SIZE,
        'other': MAX_OTHER_SIZE
    }
    return sizes.get(file_type, MAX_OTHER_SIZE)

def validate_file_size(file_size_bytes, file_type):
    """Check if file size is within limits"""
    max_size_bytes = get_max_size_mb(file_type) * 1024 * 1024
    return file_size_bytes <= max_size_bytes

def get_mime_type(filename):
    """Get MIME type from filename"""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'

def save_uploaded_file(uploaded_file):
    """Save an uploaded file to the assets directory"""
    # Create date-based subdirectory
    now = datetime.now()
    subdir = ASSETS_DIR / str(now.year) / f"{now.month:02d}"
    subdir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    original_name = uploaded_file.name
    base_name = Path(original_name).stem
    extension = Path(original_name).suffix

    # Add timestamp to avoid conflicts
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    unique_name = f"{base_name}_{timestamp}{extension}"

    file_path = subdir / unique_name

    # Write file
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    # Return relative path from media root for Django FileField
    relative_path = f"assets/{now.year}/{now.month:02d}/{unique_name}"

    return str(file_path), relative_path

def format_file_size(size_bytes):
    """Format file size for display"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def get_file_icon(file_type):
    """Get emoji icon for file type"""
    icons = {
        'image': '\U0001F5BC',  # framed picture
        'video': '\U0001F3AC',  # clapper board
        'document': '\U0001F4C4',  # page facing up
        'other': '\U0001F4C1'  # file folder
    }
    return icons.get(file_type, '\U0001F4C1')
