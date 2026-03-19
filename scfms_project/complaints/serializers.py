# complaints/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Complaint, Notification, GovernmentWhitelist, Department, DepartmentAssignment

User = get_user_model()

class PublicCitizenRegistrationSerializer(serializers.ModelSerializer):
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
            role='PC'
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
    
    class Meta:
        model = Complaint
        fields = [
            'id', 'title', 'description', 'image',
            'latitude', 'longitude', 'category', 'category_display',
            'status', 'status_display', 'severity_score',
            'user_email', 'user_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email


class NotificationSerializer(serializers.ModelSerializer):
    complaint_title = serializers.ReadOnlyField(source='complaint.title')

    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'created_at', 'complaint_title']


class GORegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    govt_id = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'govt_id', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def validate_govt_id(self, value):
        if not GovernmentWhitelist.objects.filter(gov_id=value, is_used=False).exists():
            raise serializers.ValidationError("Invalid Government ID or ID already in use.")
        if User.objects.filter(govt_id=value).exists():
            raise serializers.ValidationError("This Government ID is already registered.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='GO',
            is_active=True,
            is_verified=True,
            govt_id=validated_data['govt_id']
        )
        GovernmentWhitelist.objects.filter(gov_id=validated_data['govt_id']).update(is_used=True)
        return user


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
