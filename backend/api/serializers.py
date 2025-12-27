from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Ticket, TicketComment, TicketAttachment, TicketCollaborator, Notification, Department, Product, TicketProductItem

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
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'category', 'category_display', 'is_active', 'ticket_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_ticket_count(self, obj):
        return obj.tickets.count()


class ProductMinimalSerializer(serializers.ModelSerializer):
    """Minimal product info for nested serialization"""
    class Meta:
        model = Product
        fields = ['id', 'name', 'category']


class TicketProductItemSerializer(serializers.ModelSerializer):
    """Serializer for ticket product items (Ads/Telegram multi-product)"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_category = serializers.CharField(source='product.category', read_only=True)

    class Meta:
        model = TicketProductItem
        fields = ['id', 'product', 'product_name', 'product_category', 'quantity', 'criteria', 'created_at']
        read_only_fields = ['id', 'product_name', 'product_category', 'criteria', 'created_at']


class TicketProductItemCreateSerializer(serializers.Serializer):
    """Serializer for creating product items within ticket creation"""
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=1000, default=1)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)
    user_department_info = DepartmentMinimalSerializer(source='user_department', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'user_department', 'user_department_info', 'department',
                  'telegram_id', 'is_approved', 'approved_by', 'approved_by_name',
                  'approved_at', 'date_joined', 'is_active',
                  'is_locked', 'locked_at', 'failed_login_attempts']
        read_only_fields = ['id', 'date_joined', 'approved_by', 'approved_by_name', 'approved_at',
                           'is_locked', 'locked_at', 'failed_login_attempts']


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
    user_department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        required=True,
        error_messages={'required': 'Department is required for all users'}
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm',
                  'first_name', 'last_name', 'user_department', 'telegram_id']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match'})
        if not attrs.get('user_department'):
            raise serializers.ValidationError({'user_department': 'Department is required'})
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
    """Serializer for updating user profile (name, email, telegram, department)"""
    user_department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'telegram_id', 'user_department']


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for nested serialization"""
    user_department_info = DepartmentMinimalSerializer(source='user_department', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role', 'user_department', 'user_department_info']


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
    collaborators = TicketCollaboratorSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    # Use annotated counts from queryset to avoid N+1 queries
    comment_count = serializers.SerializerMethodField()
    attachment_count = serializers.SerializerMethodField()
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    file_format_display = serializers.CharField(source='get_file_format_display', read_only=True)
    criteria_display = serializers.SerializerMethodField()
    product_items = TicketProductItemSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'requester', 'assigned_to', 'pending_approver',
                  'status', 'priority', 'deadline', 'created_at', 'is_overdue',
                  'comment_count', 'attachment_count', 'ticket_product', 'target_department',
                  'product', 'department', 'is_deleted', 'deleted_at',
                  'request_type', 'request_type_display', 'file_format', 'file_format_display',
                  'revision_count', 'quantity', 'criteria', 'criteria_display', 'product_items',
                  'collaborators']

    def get_comment_count(self, obj):
        # Use annotated count if available, otherwise fallback to query
        return getattr(obj, 'comment_count_annotated', obj.comments.count())

    def get_attachment_count(self, obj):
        # Use annotated count if available, otherwise fallback to query
        return getattr(obj, 'attachment_count_annotated', obj.attachments.count())

    def get_criteria_display(self, obj):
        # Default to "Video" for old tickets without criteria set
        if obj.criteria:
            return obj.get_criteria_display()
        return 'Video'


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
    deleted_by = UserMinimalSerializer(read_only=True)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    file_format_display = serializers.CharField(source='get_file_format_display', read_only=True)
    criteria_display = serializers.SerializerMethodField()
    product_items = TicketProductItemSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'description', 'requester', 'assigned_to',
                  'approver', 'pending_approver', 'status', 'priority', 'deadline',
                  'created_at', 'updated_at', 'is_overdue', 'is_idle', 'comments',
                  'attachments', 'collaborators', 'confirmed_by_requester', 'confirmed_at',
                  'approved_at', 'rejected_at', 'assigned_at', 'started_at', 'completed_at',
                  'scheduled_start', 'scheduled_end', 'actual_end',
                  'ticket_product', 'target_department', 'product', 'department',
                  'complexity', 'estimated_hours', 'actual_hours',
                  'is_deleted', 'deleted_at', 'deleted_by',
                  'request_type', 'request_type_display', 'file_format', 'file_format_display',
                  'revision_count', 'quantity', 'criteria', 'criteria_display', 'product_items']

    def get_comments(self, obj):
        # Only return top-level comments (replies are nested within them)
        top_level_comments = obj.comments.filter(parent__isnull=True)
        return TicketCommentSerializer(top_level_comments, many=True).data

    def get_criteria_display(self, obj):
        # Default to "Video" for old tickets without criteria set
        if obj.criteria:
            return obj.get_criteria_display()
        return 'Video'


class TicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tickets"""
    product_items = TicketProductItemCreateSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'description', 'priority', 'assigned_to',
                  'ticket_product', 'target_department', 'product', 'department',
                  'complexity', 'estimated_hours', 'request_type', 'file_format',
                  'quantity', 'criteria', 'product_items']
        read_only_fields = ['id']

    def validate(self, attrs):
        request_type = attrs.get('request_type', '')
        file_format = attrs.get('file_format', '')
        product_items = attrs.get('product_items', [])
        quantity = attrs.get('quantity', 1)

        # Validate file_format is only allowed for socmed_posting request type
        if file_format and request_type != 'socmed_posting':
            raise serializers.ValidationError({
                'file_format': 'File format is only applicable for Socmed Posting requests'
            })

        # Validate quantity limit
        if quantity > 1000:
            raise serializers.ValidationError({
                'quantity': 'Quantity cannot exceed 1000'
            })

        # For Ads/Telegram, product_items are required
        if request_type in ['ads', 'telegram_channel']:
            if not product_items:
                raise serializers.ValidationError({
                    'product_items': 'Product items are required for Ads and Telegram requests'
                })
            # Validate total quantity across product items
            total_qty = sum(item.get('quantity', 1) for item in product_items)
            if total_qty > 1000:
                raise serializers.ValidationError({
                    'product_items': 'Total quantity across all products cannot exceed 1000'
                })

        # Auto-set criteria based on request type and file format
        if request_type == 'socmed_posting' and file_format:
            if file_format in ['still', 'gif']:
                attrs['criteria'] = 'image'
            elif file_format in ['video_landscape', 'video_portrait']:
                attrs['criteria'] = 'video'

        return attrs

    def create(self, validated_data):
        product_items_data = validated_data.pop('product_items', [])
        validated_data['requester'] = self.context['request'].user
        ticket = super().create(validated_data)

        # Create product items for Ads/Telegram requests
        for item_data in product_items_data:
            TicketProductItem.objects.create(
                ticket=ticket,
                product=item_data['product'],
                quantity=item_data.get('quantity', 1)
            )

        return ticket


class TicketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tickets"""

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'assigned_to',
                  'ticket_product', 'target_department', 'product', 'department',
                  'complexity', 'estimated_hours', 'actual_hours',
                  'is_deleted', 'deleted_at', 'deleted_by',
                  'request_type', 'file_format', 'quantity', 'criteria']


class RevisionRequestSerializer(serializers.Serializer):
    """Serializer for requesting revision on a ticket"""
    revision_comments = serializers.CharField(required=True, min_length=1)


class TicketAssignSerializer(serializers.Serializer):
    """Serializer for assigning ticket"""
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    scheduled_start = serializers.DateTimeField(required=False, allow_null=True)
    scheduled_end = serializers.DateTimeField(required=False, allow_null=True)


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
