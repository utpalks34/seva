# complaints/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


# ============================================================
#                   CUSTOM USER MANAGER
# ============================================================
class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)   # no username here
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "GO")  # admin is not citizen

        return self.create_user(email, password, **extra_fields)


# ============================================================
#                     CUSTOM USER MODEL
# ============================================================
class User(AbstractUser):
    username = None   # completely disable username

    email = models.EmailField(unique=True)

    ROLE_CHOICES = (
        ('PC', 'Public Citizen'),
        ('GO', 'Government Official'),
    )
    role = models.CharField(max_length=2, choices=ROLE_CHOICES, default='PC')

    govt_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []   # no username required

    objects = UserManager()   # <-- THIS FIXES THE ERROR

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"


# ============================================================
#                     COMPLAINT MODEL
# ============================================================
class Complaint(models.Model):

    CATEGORY_CHOICES = (
        ('RO', 'Roads/Potholes'),
        ('GA', 'Garbage/Waste'),
        ('UT', 'Utilities (Water/Power)'),
        ('PB', 'Public Behavior'),
        ('OT', 'Other'),
    )

    STATUS_CHOICES = (
        ('P', 'Pending'),
        ('I', 'In Progress'),
        ('R', 'Resolved'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')

    title = models.CharField(max_length=150)
    description = models.TextField()

    image = models.ImageField(upload_to='complaint_images/')

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    category = models.CharField(max_length=2, choices=CATEGORY_CHOICES, default='OT')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')

    severity_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    # Duplicate detection fields
    is_duplicate = models.BooleanField(default=False)
    original_complaint = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='duplicates'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-severity_score', '-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title} by {self.user.email}"


# ============================================================
#                    NOTIFICATION MODEL
# ============================================================
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.email}: {self.message[:30]}..."


# ============================================================
#                  GOVERNMENT WHITELIST
# ============================================================
class GovernmentWhitelist(models.Model):
    gov_id = models.CharField(max_length=50, unique=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return self.gov_id


# ============================================================
#                    DEPARTMENT MODEL
# ============================================================
class Department(models.Model):
    """
    Represents government departments that handle different complaint categories.
    Stores contact info for auto-routing notifications.
    """
    
    CATEGORY_CHOICES = (
        ('RO', 'Roads & Potholes'),
        ('GA', 'Garbage & Waste'),
        ('UT', 'Utilities (Water/Power)'),
        ('PB', 'Public Buildings'),
        ('OT', 'Other'),
    )
    
    category = models.CharField(max_length=2, choices=CATEGORY_CHOICES, unique=True)
    department_name = models.CharField(max_length=100)
    department_head_name = models.CharField(max_length=100)
    department_head_email = models.EmailField()
    department_head_phone = models.CharField(max_length=15, blank=True)
    office_address = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category']
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.department_name}"


# ============================================================
#                DEPARTMENT ASSIGNMENT MODEL
# ============================================================
class DepartmentAssignment(models.Model):
    """
    Tracks which complaint is assigned to which department.
    Maintains routing history and assignment status.
    """
    
    STATUS_CHOICES = (
        ('ASSIGNED', 'Assigned'),
        ('ACKNOWLEDGED', 'Department Acknowledged'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
    )
    
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='department_assignments')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_complaints')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ASSIGNED')
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-assigned_at']
        unique_together = ('complaint', 'department')
    
    def __str__(self):
        return f"Complaint #{self.complaint.id} → {self.department.get_category_display()}"
