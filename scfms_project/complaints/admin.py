from django.contrib import admin
from django.utils.html import format_html
from .models import User, Complaint, Notification, GovernmentWhitelist, Department, DepartmentAssignment


# ============================================================
#                     USER ADMIN
# ============================================================
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'role_badge', 'govt_id', 'is_active', 'is_verified', 'date_joined')
    list_filter = ('role', 'is_active', 'is_verified', 'date_joined')
    search_fields = ('email', 'govt_id', 'first_name', 'last_name')
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        ('Account Info', {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Government', {'fields': ('govt_id', 'role')}),
        ('Status', {'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser')}),
        ('Dates', {'fields': ('date_joined', 'last_login')}),
    )
    
    def role_badge(self, obj):
        colors = {'PC': '#0066cc', 'GO': '#ff6600', 'AD': '#7c3aed'}
        color = colors.get(obj.role, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_role_display()
        )
    role_badge.short_description = 'Role'


# ============================================================
#                  COMPLAINT ADMIN
# ============================================================
@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('id', 'title_short', 'category_badge', 'severity_badge', 'status_badge', 'user_email', 'created_at', 'routed_status')
    list_filter = ('category', 'status', 'severity_score', 'created_at')
    search_fields = ('title', 'description', 'user__email')
    readonly_fields = ('created_at', 'image_preview')
    
    fieldsets = (
        ('Complaint Details', {'fields': ('title', 'description', 'category', 'status')}),
        ('Reporter', {'fields': ('user',)}),
        ('Image', {'fields': ('image', 'image_preview')}),
        ('Location', {'fields': ('latitude', 'longitude')}),
        ('Severity', {'fields': ('severity_score',)}),
        ('Dates', {'fields': ('created_at',)}),
    )
    
    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Title'
    
    def category_badge(self, obj):
        colors = {
            'RO': '#FF6B6B',  # Red
            'GA': '#FFA500',  # Orange
            'UT': '#4ECDC4',  # Teal
            'PB': '#95E1D3',  # Mint
            'OT': '#A8A8A8',  # Gray
        }
        color = colors.get(obj.category, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_category_display()
        )
    category_badge.short_description = 'Category'
    
    def severity_badge(self, obj):
        if obj.severity_score >= 75:
            color = '#FF4444'
            label = f'🔴 Critical ({obj.severity_score})'
        elif obj.severity_score >= 50:
            color = '#FFA500'
            label = f'🟠 High ({obj.severity_score})'
        else:
            color = '#FFD700'
            label = f'🟡 Low ({obj.severity_score})'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            label
        )
    severity_badge.short_description = 'Severity'
    
    def status_badge(self, obj):
        colors = {'P': '#FFA500', 'I': '#4ECDC4', 'R': '#52C41A'}
        color = colors.get(obj.status, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Reporter Email'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px;" />',
                obj.image.url
            )
        return 'No image'
    image_preview.short_description = 'Image Preview'
    
    def routed_status(self, obj):
        assignments = obj.department_assignments.all()
        if assignments.exists():
            return format_html(
                '✅ Routed to {} department(s)',
                assignments.count()
            )
        return format_html('❌ Not routed')
    routed_status.short_description = 'Routing Status'


# ============================================================
#              DEPARTMENT ADMIN
# ============================================================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('category_display', 'department_name', 'department_head_name', 'department_head_email', 'status_badge', 'assignment_count')
    list_filter = ('category', 'is_active')
    search_fields = ('department_name', 'department_head_name', 'department_head_email')
    
    fieldsets = (
        ('Department Info', {'fields': ('category', 'department_name')}),
        ('Department Head', {'fields': ('department_head_name', 'department_head_email', 'department_head_phone')}),
        ('Contact', {'fields': ('office_address',)}),
        ('Status', {'fields': ('is_active',)}),
    )
    
    def category_display(self, obj):
        return obj.get_category_display()
    category_display.short_description = 'Category'
    
    def status_badge(self, obj):
        color = '#52C41A' if obj.is_active else '#FF4444'
        label = '✅ Active' if obj.is_active else '❌ Inactive'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            label
        )
    status_badge.short_description = 'Status'
    
    def assignment_count(self, obj):
        count = obj.assignments.count()
        return format_html(
            '<strong>{}</strong> complaint(s)',
            count
        )
    assignment_count.short_description = 'Assigned Complaints'


# ============================================================
#          DEPARTMENT ASSIGNMENT ADMIN
# ============================================================
@admin.register(DepartmentAssignment)
class DepartmentAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'complaint_title', 'department_name', 'status_badge', 'assigned_at', 'notification_status')
    list_filter = ('status', 'assigned_at', 'department')
    search_fields = ('complaint__title', 'department__department_name')
    readonly_fields = ('assigned_at', 'notification_sent_at', 'acknowledged_at', 'resolved_at')
    
    fieldsets = (
        ('Assignment', {'fields': ('complaint', 'department', 'assigned_by')}),
        ('Status', {'fields': ('status', 'notes')}),
        ('Notification', {'fields': ('notification_sent', 'notification_sent_at')}),
        ('Timeline', {'fields': ('assigned_at', 'acknowledged_at', 'resolved_at')}),
    )
    
    def complaint_title(self, obj):
        return obj.complaint.title[:40]
    complaint_title.short_description = 'Complaint'
    
    def department_name(self, obj):
        return obj.department.department_name
    department_name.short_description = 'Department'
    
    def status_badge(self, obj):
        colors = {
            'ASSIGNED': '#FFA500',
            'ACKNOWLEDGED': '#4ECDC4',
            'IN_PROGRESS': '#87CEEB',
            'RESOLVED': '#52C41A',
        }
        color = colors.get(obj.status, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def notification_status(self, obj):
        if obj.notification_sent:
            return format_html('✅ Sent at {}', obj.notification_sent_at.strftime('%Y-%m-%d %H:%M'))
        return format_html('❌ Not sent')
    notification_status.short_description = 'Notification'


# ============================================================
#            NOTIFICATION ADMIN
# ============================================================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'message_short', 'is_read_badge', 'complaint_title', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__email', 'message', 'complaint__title')
    readonly_fields = ('created_at',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    
    def message_short(self, obj):
        return obj.message[:60] + '...' if len(obj.message) > 60 else obj.message
    message_short.short_description = 'Message'
    
    def is_read_badge(self, obj):
        color = '#52C41A' if obj.is_read else '#FFA500'
        label = '✅ Read' if obj.is_read else '❌ Unread'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            label
        )
    is_read_badge.short_description = 'Status'
    
    def complaint_title(self, obj):
        if obj.complaint:
            return obj.complaint.title[:30]
        return '-'
    complaint_title.short_description = 'Complaint'


# ============================================================
#         GOVERNMENT WHITELIST ADMIN
# ============================================================
@admin.register(GovernmentWhitelist)
class GovernmentWhitelistAdmin(admin.ModelAdmin):
    list_display = ('gov_id', 'is_used_badge')
    list_filter = ('is_used',)
    search_fields = ('gov_id',)
    
    def is_used_badge(self, obj):
        color = '#52C41A' if obj.is_used else '#FFA500'
        label = '✅ Used' if obj.is_used else '❌ Available'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            label
        )
    is_used_badge.short_description = 'Status'
