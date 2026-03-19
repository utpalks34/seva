# complaints/department_routing.py

"""
Department Routing Service

Handles automatic routing of complaints to appropriate government departments
based on category classification. Sends email/SMS notifications to departments.
"""

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import logging

from .models import Complaint, Department, DepartmentAssignment, Notification

logger = logging.getLogger(__name__)


# ============================================================
# DEPARTMENT ROUTING SERVICE
# ============================================================
class DepartmentRoutingService:
    """
    Auto-routes complaints to appropriate government departments
    and sends notifications.
    """
    
    @staticmethod
    def route_complaint(complaint):
        """
        Route a complaint to the appropriate department based on category.
        
        Args:
            complaint (Complaint): The complaint to route
            
        Returns:
            DepartmentAssignment: The created assignment, or None if failed
        """
        try:
            print(f"🔄 Starting routing for complaint #{complaint.id}: {complaint.title}")
            
            # Get department for this category
            department = Department.objects.filter(
                category=complaint.category,
                is_active=True
            ).first()
            
            if not department:
                print(f"⚠️  No active department found for category: {complaint.get_category_display()}")
                # Create generic assignment for unknown departments
                department = Department.objects.filter(
                    category='OT',
                    is_active=True
                ).first()
                
                if not department:
                    print(f"❌ No 'Other' department configured. Skipping routing.")
                    return None
            
            print(f"✅ Found department: {department.department_name}")
            
            # Create department assignment
            assignment, created = DepartmentAssignment.objects.get_or_create(
                complaint=complaint,
                department=department,
                defaults={'status': 'ASSIGNED'}
            )
            
            if created:
                print(f"✅ Department assignment created: {assignment.id}")
            else:
                print(f"ℹ️  Assignment already exists for this complaint")
                return assignment
            
            # Send notification to department
            success = DepartmentRoutingService.send_department_notification(
                complaint=complaint,
                department=department,
                assignment=assignment
            )
            
            if success:
                assignment.notification_sent = True
                assignment.notification_sent_at = timezone.now()
                assignment.save()
                print(f"✅ Notification sent to department")
            else:
                print(f"⚠️  Failed to send notification to department")
            
            # Create notification for department (in-app)
            DepartmentRoutingService.create_department_notification(
                complaint=complaint,
                department=department
            )
            
            print(f"✅ Routing complete for complaint #{complaint.id}")
            return assignment
            
        except Exception as e:
            print(f"❌ Error routing complaint: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    
    @staticmethod
    def send_department_notification(complaint, department, assignment):
        """
        Send email notification to department.
        
        Args:
            complaint (Complaint): The complaint
            department (Department): The target department
            assignment (DepartmentAssignment): The assignment record
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Build email content
            subject = f"🔔 New {complaint.get_category_display()} Complaint - Severity: {complaint.severity_score}/100"
            
            complaint_url = f"{settings.SITE_URL}/go-dashboard/" if hasattr(settings, 'SITE_URL') else "Your complaint dashboard"
            
            message = f"""
Dear {department.department_head_name},

A new complaint has been assigned to {department.department_name} for review and action.

COMPLAINT DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Title: {complaint.title}
Category: {complaint.get_category_display()}
Severity Score: {complaint.severity_score}/100
Description: {complaint.description}

LOCATION:
Latitude: {complaint.latitude}
Longitude: {complaint.longitude}

REPORTER:
Name: {complaint.user.get_full_name() or complaint.user.email}
Email: {complaint.user.email}
Phone: {complaint.user.phone_number if hasattr(complaint.user, 'phone_number') else 'N/A'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ACTION REQUIRED:
1. Review the complaint details and image
2. Log into your dashboard: {complaint_url}
3. Update complaint status (In Progress → Resolved)
4. Add action notes/updates as needed

⏰ Priority: {"HIGH" if complaint.severity_score >= 75 else "MEDIUM" if complaint.severity_score >= 50 else "LOW"}

Assignment ID: {assignment.id}
Assignment Date: {assignment.assigned_at.strftime('%Y-%m-%d %H:%M:%S')}

Please acknowledge receipt of this complaint within 24 hours.

---
This is an automated message from SCFMS (Smart Civic Facility Management System)
Do not reply to this email. Use your dashboard to respond.
"""
            
            # Send email
            sent = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[department.department_head_email],
                fail_silently=False,
            )
            
            print(f"📧 Email sent to {department.department_head_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email: {str(e)}")
            return False
    
    
    @staticmethod
    def create_department_notification(complaint, department):
        """
        Create in-app notification for the department (to department staff).
        
        Args:
            complaint (Complaint): The complaint
            department (Department): The target department
        """
        try:
            # Find government users in this department (if we have dept_user link)
            # For now, create a generic notification
            message = f"""
New complaint assigned: {complaint.title}
Category: {complaint.get_category_display()}
Severity: {complaint.severity_score}/100
Location: Lat {complaint.latitude}, Lon {complaint.longitude}
Reporter: {complaint.user.email}
"""
            
            # Could create notifications for specific users in department
            # For now, log it
            print(f"📬 In-app notification created for department: {message[:50]}...")
            
        except Exception as e:
            print(f"❌ Error creating in-app notification: {str(e)}")


# ============================================================
# DEPARTMENT ASSIGNMENT STATUS UPDATES
# ============================================================
class DepartmentAssignmentService:
    """
    Handles updates to department assignments (status changes, acknowledgments, etc).
    """
    
    @staticmethod
    def acknowledge_assignment(assignment):
        """
        Department acknowledges receipt of complaint.
        
        Args:
            assignment (DepartmentAssignment): The assignment to acknowledge
        """
        assignment.status = 'ACKNOWLEDGED'
        assignment.acknowledged_at = timezone.now()
        assignment.save()
        print(f"✅ Assignment #{assignment.id} acknowledged by {assignment.department.department_name}")
    
    
    @staticmethod
    def mark_in_progress(assignment, notes=""):
        """
        Mark assignment as in progress.
        
        Args:
            assignment (DepartmentAssignment): The assignment
            notes (str): Action notes
        """
        assignment.status = 'IN_PROGRESS'
        if notes:
            assignment.notes = notes
        assignment.save()
        print(f"🔄 Assignment #{assignment.id} marked as IN_PROGRESS")
    
    
    @staticmethod
    def mark_resolved(assignment, notes=""):
        """
        Mark assignment (and complaint) as resolved.
        
        Args:
            assignment (DepartmentAssignment): The assignment
            notes (str): Resolution notes
        """
        assignment.status = 'RESOLVED'
        assignment.resolved_at = timezone.now()
        if notes:
            assignment.notes = notes
        assignment.save()
        
        # Mark complaint as resolved if all assignments are resolved
        complaint = assignment.complaint
        all_assignments = DepartmentAssignment.objects.filter(complaint=complaint)
        if all(a.status == 'RESOLVED' for a in all_assignments):
            complaint.status = 'R'
            complaint.save()
            print(f"✅ Complaint #{complaint.id} marked as RESOLVED")
        
        print(f"✅ Assignment #{assignment.id} marked as RESOLVED")
    
    
    @staticmethod
    def get_assignment_status(complaint):
        """
        Get routing status of a complaint across all departments.
        
        Args:
            complaint (Complaint): The complaint
            
        Returns:
            dict: Status information
        """
        assignments = DepartmentAssignment.objects.filter(complaint=complaint)
        
        return {
            'total_assignments': assignments.count(),
            'assigned': assignments.filter(status='ASSIGNED').count(),
            'acknowledged': assignments.filter(status='ACKNOWLEDGED').count(),
            'in_progress': assignments.filter(status='IN_PROGRESS').count(),
            'resolved': assignments.filter(status='RESOLVED').count(),
            'assignments': list(assignments.values('id', 'department__department_name', 'status', 'assigned_at'))
        }


# ============================================================
# BULK OPERATIONS
# ============================================================
def route_all_unrouted_complaints():
    """
    Route all complaints that haven't been assigned yet.
    Useful for batch processing.
    """
    try:
        unrouted = Complaint.objects.filter(
            department_assignments__isnull=True
        ).distinct()
        
        print(f"🔄 Processing {unrouted.count()} unrouted complaints...")
        
        count = 0
        for complaint in unrouted:
            result = DepartmentRoutingService.route_complaint(complaint)
            if result:
                count += 1
        
        print(f"✅ Successfully routed {count}/{unrouted.count()} complaints")
        return count
        
    except Exception as e:
        print(f"❌ Error in bulk routing: {str(e)}")
        return 0
