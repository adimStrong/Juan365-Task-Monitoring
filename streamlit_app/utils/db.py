"""Database connection using Django ORM"""
import os
import sys
from pathlib import Path

# Add backend to Python path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / 'backend'
sys.path.insert(0, str(BACKEND_DIR))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticketing.settings')

import django
django.setup()

# Now we can import Django models
from api.models import User, Ticket, FileAsset

def get_all_files(file_type=None, search=None, limit=100):
    """Get all file assets with optional filtering"""
    queryset = FileAsset.objects.all()

    if file_type and file_type != 'all':
        queryset = queryset.filter(file_type=file_type)

    if search:
        queryset = queryset.filter(name__icontains=search)

    return queryset[:limit]

def get_file_by_id(file_id):
    """Get a single file by ID"""
    try:
        return FileAsset.objects.get(id=file_id)
    except FileAsset.DoesNotExist:
        return None

def create_file_asset(name, file_path, file_type, mime_type, file_size, description='', tags='', user_id=None, ticket_id=None):
    """Create a new file asset record"""
    asset = FileAsset(
        name=name,
        file=file_path,
        file_type=file_type,
        mime_type=mime_type,
        file_size=file_size,
        description=description,
        tags=tags,
    )

    if user_id:
        try:
            asset.uploaded_by = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass

    if ticket_id:
        try:
            asset.ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            pass

    asset.save()
    return asset

def delete_file_asset(file_id):
    """Delete a file asset"""
    try:
        asset = FileAsset.objects.get(id=file_id)
        # Delete the actual file
        if asset.file:
            file_path = asset.file.path
            if os.path.exists(file_path):
                os.remove(file_path)
        asset.delete()
        return True
    except FileAsset.DoesNotExist:
        return False

def get_file_stats():
    """Get file statistics"""
    from django.db.models import Sum, Count

    stats = FileAsset.objects.aggregate(
        total_files=Count('id'),
        total_size=Sum('file_size'),
        image_count=Count('id', filter=django.db.models.Q(file_type='image')),
        video_count=Count('id', filter=django.db.models.Q(file_type='video')),
        document_count=Count('id', filter=django.db.models.Q(file_type='document')),
        other_count=Count('id', filter=django.db.models.Q(file_type='other')),
    )

    return stats

def get_all_users():
    """Get all active users for dropdown"""
    return User.objects.filter(is_active=True, is_approved=True).values('id', 'username', 'first_name', 'last_name')

def get_all_tickets():
    """Get all tickets for linking"""
    return Ticket.objects.all().values('id', 'title')[:50]
