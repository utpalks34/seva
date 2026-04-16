# complaints/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Complaint, Notification, GovernmentWhitelist, Department, DepartmentAssignment

User = get_user_model()


class StrongPasswordMixin:
    def validate_password(self, value):
        validate_password(value)
        if (
            not any(ch.isupper() for ch in value)
            or not any(ch.islower() for ch in value)
            or not any(ch.isdigit() for ch in value)
            or not any(not ch.isalnum() for ch in value)
        ):
            raise serializers.ValidationError(
                "Password must include uppercase, lowercase, number, and special character."
            )
        return value


class PublicCitizenRegistrationSerializer(StrongPasswordMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Use create_user from your custom manager (no username)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='PC',
            is_verified=False,
        )
        return user


class ComplaintRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = [
            'title', 'description', 'image',
            'latitude', 'longitude', 'category'
        ]
        read_only_fields = ['category']


class ComplaintListSerializer(serializers.ModelSerializer):
    """Serializer for listing complaints (includes all fields for government dashboard)"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    resolution_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Complaint
        fields = [
            'id', 'title', 'description', 'image',
            'latitude', 'longitude', 'category', 'category_display',
            'status', 'status_display', 'severity_score',
            'user_email', 'user_name', 'created_at', 'resolved_at',
            'resolution_image_url'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_resolution_image_url(self, obj):
        if obj.resolution_image:
            request = self.context.get('request')
            url = obj.resolution_image.url
            return request.build_absolute_uri(url) if request else url
        return None


class NotificationSerializer(serializers.ModelSerializer):
    complaint_title = serializers.ReadOnlyField(source='complaint.title')
    complaint_id = serializers.ReadOnlyField(source='complaint.id')
    resolution_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'created_at', 'complaint_title', 'complaint_id', 'resolution_image_url']

    def get_resolution_image_url(self, obj):
        complaint = obj.complaint
        if complaint and complaint.resolution_image:
            request = self.context.get('request')
            url = complaint.resolution_image.url
            return request.build_absolute_uri(url) if request else url
        return None


class GORegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'govt_id', 'first_name', 'last_name')

    def validate(self, attrs):
        raise serializers.ValidationError(
            "Government self-registration is disabled. Contact an administrator."
        )


class GovernmentInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name')

    def validate_email(self, value):
        value = value.lower().strip()
        if not value.endswith('@gov.in'):
            raise serializers.ValidationError("Government users must use an official @gov.in email.")
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        return User.objects.create_user(
            email=validated_data['email'],
            password=None,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='GO',
            is_active=False,
            is_verified=False,
            invited_by=request.user,
        )


class GovernmentActivationSerializer(StrongPasswordMixin, serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)


class UserAdminSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'role', 'role_display',
            'is_active', 'is_verified', 'otp_enabled', 'date_joined'
        )


class UserStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('is_active', 'otp_enabled')


# ============================================================
#              DEPARTMENT SERIALIZERS
# ============================================================
class DepartmentSerializer(serializers.ModelSerializer):
    category_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'category', 'category_display', 'department_name',
            'department_head_name', 'department_head_email', 'department_head_phone',
            'office_address', 'is_active'
        ]
    
    def get_category_display(self, obj):
        return obj.get_category_display()


class DepartmentAssignmentSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.department_name', read_only=True)
    complaint_title = serializers.CharField(source='complaint.title', read_only=True)
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = DepartmentAssignment
        fields = [
            'id', 'complaint', 'complaint_title', 'department', 'department_name',
            'assigned_at', 'status', 'status_display', 'notification_sent',
            'acknowledged_at', 'resolved_at', 'notes'
        ]
        read_only_fields = [
            'assigned_at', 'notification_sent_at', 'acknowledged_at', 'resolved_at'
        ]
    
    def get_status_display(self, obj):
        return obj.get_status_display()
