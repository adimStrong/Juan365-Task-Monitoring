from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Ticket, TicketComment, TicketAttachment, Notification, ActivityLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin with extra fields"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_approved', 'is_active')
    list_filter = ('role', 'is_approved', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('role', 'is_approved', 'approved_by', 'approved_at', 'telegram_id')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Extra Info', {'fields': ('role', 'is_approved')}),
    )


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'priority', 'requester', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'user', 'created_at')
    list_filter = ('created_at',)
    ordering = ('-created_at',)


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'file_name', 'user', 'uploaded_at')
    ordering = ('-uploaded_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    ordering = ('-created_at',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'ticket', 'action', 'created_at')
    list_filter = ('action', 'created_at')
    ordering = ('-created_at',)
