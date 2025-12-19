from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Ticket, TicketComment, TicketAttachment, Notification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'department', 'telegram_id', 'is_approved',
                  'approved_by', 'approved_by_name', 'approved_at', 'date_joined', 'is_active']
        read_only_fields = ['id', 'date_joined', 'approved_by', 'approved_by_name', 'approved_at']


class UserManagementSerializer(serializers.ModelSerializer):
    """Serializer for admin user management"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'department', 'is_approved', 'is_active']
        read_only_fields = ['id', 'username', 'email']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm',
                  'first_name', 'last_name', 'department', 'telegram_id']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for nested serialization"""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class TicketCommentSerializer(serializers.ModelSerializer):
    """Serializer for ticket comments"""
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = TicketComment
        fields = ['id', 'ticket', 'user', 'comment', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class TicketAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for ticket attachments"""
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = TicketAttachment
        fields = ['id', 'ticket', 'user', 'file', 'file_name', 'uploaded_at']
        read_only_fields = ['id', 'user', 'uploaded_at']


class TicketListSerializer(serializers.ModelSerializer):
    """Serializer for ticket list view"""
    requester = UserMinimalSerializer(read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'requester', 'assigned_to', 'status',
                  'priority', 'deadline', 'created_at', 'is_overdue', 'comment_count']

    def get_comment_count(self, obj):
        return obj.comments.count()


class TicketDetailSerializer(serializers.ModelSerializer):
    """Serializer for ticket detail view"""
    requester = UserMinimalSerializer(read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    approver = UserMinimalSerializer(read_only=True)
    comments = TicketCommentSerializer(many=True, read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_idle = serializers.BooleanField(read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'description', 'requester', 'assigned_to',
                  'approver', 'status', 'priority', 'deadline', 'created_at',
                  'updated_at', 'is_overdue', 'is_idle', 'comments', 'attachments']


class TicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tickets"""

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'deadline', 'assigned_to']

    def create(self, validated_data):
        validated_data['requester'] = self.context['request'].user
        return super().create(validated_data)


class TicketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tickets"""

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'deadline', 'assigned_to']


class TicketAssignSerializer(serializers.Serializer):
    """Serializer for assigning ticket"""
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())


class TicketRejectSerializer(serializers.Serializer):
    """Serializer for rejecting ticket with reason"""
    reason = serializers.CharField(required=False, allow_blank=True)


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    ticket_title = serializers.CharField(source='ticket.title', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'ticket', 'ticket_title', 'message', 'notification_type',
                  'is_read', 'telegram_sent', 'created_at']
        read_only_fields = ['id', 'ticket', 'message', 'notification_type',
                           'telegram_sent', 'created_at']


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_tickets = serializers.IntegerField()
    pending_approval = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    completed = serializers.IntegerField()
    overdue = serializers.IntegerField()
    my_assigned = serializers.IntegerField()


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for activity logs"""
    user = UserMinimalSerializer(read_only=True)
    ticket_title = serializers.CharField(source='ticket.title', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        from .models import ActivityLog
        model = ActivityLog
        fields = ['id', 'user', 'ticket', 'ticket_title', 'action', 'action_display',
                  'details', 'created_at']
        read_only_fields = ['id', 'user', 'ticket', 'action', 'details', 'created_at']
