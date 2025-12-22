from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Ticket, TicketComment, TicketAttachment, TicketCollaborator, Notification, Department, Product

User = get_user_model()


# =====================
# DEPARTMENT & PRODUCT SERIALIZERS
# =====================

class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for departments"""
    manager = serializers.SerializerMethodField()
    manager_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='manager',
        write_only=True,
        required=False,
        allow_null=True
    )
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'manager', 'manager_id', 'is_creative', 'is_active', 'member_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_manager(self, obj):
        if obj.manager:
            return {
                'id': obj.manager.id,
                'username': obj.manager.username,
                'first_name': obj.manager.first_name,
                'last_name': obj.manager.last_name,
                'role': obj.manager.role
            }
        return None

    def get_member_count(self, obj):
        return obj.members.count()


class DepartmentMinimalSerializer(serializers.ModelSerializer):
    """Minimal department info for nested serialization"""
    class Meta:
        model = Department
        fields = ['id', 'name', 'is_creative']


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for products"""
    ticket_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'is_active', 'ticket_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_ticket_count(self, obj):
        return obj.tickets.count()


class ProductMinimalSerializer(serializers.ModelSerializer):
    """Minimal product info for nested serialization"""
    class Meta:
        model = Product
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)
    user_department_info = DepartmentMinimalSerializer(source='user_department', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'user_department', 'user_department_info', 'department',
                  'telegram_id', 'is_approved', 'approved_by', 'approved_by_name',
                  'approved_at', 'date_joined', 'is_active']
        read_only_fields = ['id', 'date_joined', 'approved_by', 'approved_by_name', 'approved_at']


class UserManagementSerializer(serializers.ModelSerializer):
    """Serializer for admin user management"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'user_department', 'department', 'is_approved', 'is_active']
        read_only_fields = ['id', 'username', 'email']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)

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


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match'})
        return attrs


class UpdateUserProfileSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile (name, email, telegram)"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'telegram_id', 'department']


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for nested serialization"""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role']


class TicketCommentSerializer(serializers.ModelSerializer):
    """Serializer for ticket comments with replies"""
    user = UserMinimalSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = TicketComment
        fields = ['id', 'ticket', 'user', 'parent', 'comment', 'created_at', 'replies']
        read_only_fields = ['id', 'ticket', 'user', 'created_at']

    def get_replies(self, obj):
        # Only get replies for top-level comments (no parent)
        if obj.parent is None:
            replies = obj.replies.all()
            return TicketCommentSerializer(replies, many=True).data
        return []


class TicketAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for ticket attachments"""
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = TicketAttachment
        fields = ['id', 'ticket', 'user', 'file', 'file_name', 'uploaded_at']
        read_only_fields = ['id', 'ticket', 'user', 'file_name', 'uploaded_at']


class TicketCollaboratorSerializer(serializers.ModelSerializer):
    """Serializer for ticket collaborators"""
    user = UserMinimalSerializer(read_only=True)
    added_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = TicketCollaborator
        fields = ['id', 'ticket', 'user', 'added_by', 'added_at']
        read_only_fields = ['id', 'added_by', 'added_at']


class TicketListSerializer(serializers.ModelSerializer):
    """Serializer for ticket list view"""
    requester = UserMinimalSerializer(read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    pending_approver = UserMinimalSerializer(read_only=True)
    ticket_product = ProductMinimalSerializer(read_only=True)
    target_department = DepartmentMinimalSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'requester', 'assigned_to', 'pending_approver',
                  'status', 'priority', 'deadline', 'created_at', 'is_overdue',
                  'comment_count', 'ticket_product', 'target_department',
                  'product', 'department']

    def get_comment_count(self, obj):
        return obj.comments.count()


class TicketDetailSerializer(serializers.ModelSerializer):
    """Serializer for ticket detail view"""
    requester = UserMinimalSerializer(read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    approver = UserMinimalSerializer(read_only=True)
    pending_approver = UserMinimalSerializer(read_only=True)
    ticket_product = ProductMinimalSerializer(read_only=True)
    target_department = DepartmentMinimalSerializer(read_only=True)
    comments = serializers.SerializerMethodField()
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    collaborators = TicketCollaboratorSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_idle = serializers.BooleanField(read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'description', 'requester', 'assigned_to',
                  'approver', 'pending_approver', 'status', 'priority', 'deadline',
                  'created_at', 'updated_at', 'is_overdue', 'is_idle', 'comments',
                  'attachments', 'collaborators', 'confirmed_by_requester', 'confirmed_at',
                  'approved_at', 'rejected_at', 'assigned_at', 'started_at', 'completed_at',
                  'ticket_product', 'target_department', 'product', 'department',
                  'complexity', 'estimated_hours', 'actual_hours']

    def get_comments(self, obj):
        # Only return top-level comments (replies are nested within them)
        top_level_comments = obj.comments.filter(parent__isnull=True)
        return TicketCommentSerializer(top_level_comments, many=True).data


class TicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tickets"""

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'description', 'priority', 'deadline', 'assigned_to',
                  'ticket_product', 'target_department', 'product', 'department',
                  'complexity', 'estimated_hours']
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['requester'] = self.context['request'].user
        return super().create(validated_data)


class TicketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tickets"""

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'deadline', 'assigned_to',
                  'ticket_product', 'target_department', 'product', 'department',
                  'complexity', 'estimated_hours', 'actual_hours']


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
        fields = ['id', 'user', 'ticket', 'ticket_title', 'action', 'action_display', 'snapshot',
                  'details', 'created_at']
        read_only_fields = ['id', 'user', 'ticket', 'action', 'details', 'snapshot', 'created_at']
