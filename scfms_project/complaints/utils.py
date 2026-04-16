# complaints/utils.py

from .models import Notification
from channels.layers import get_channel_layer # <-- NEW
from asgiref.sync import async_to_sync # <-- NEW
from django.utils import timezone
import json

def create_notification(user, message, complaint=None):
    """Creates a notification for a specific user and sends it via WebSocket."""
    # 1. Save the notification to the database
    Notification.objects.create(
        user=user,
        message=message,
        complaint=complaint
    )
    
    # 2. Send the message via WebSocket (Real-Time Push)
    channel_layer = get_channel_layer()
    user_group_name = f'user_{user.id}'
    resolution_image_url = complaint.resolution_image.url if complaint and complaint.resolution_image else None
    
    # Use async_to_sync because this utility is called from a synchronous DRF view
    async_to_sync(channel_layer.group_send)(
        user_group_name,
        {
            'type': 'send_notification', # Maps to the consumer method name
            'message': message,
            'timestamp': timezone.now().isoformat(),
            'complaint_id': complaint.id if complaint else None,
            'resolution_image_url': resolution_image_url,
        }
    )


def broadcast_complaint_to_gos(complaint):
    """
    🚨 Broadcast a new complaint to ALL Government Officials via WebSocket.
    
    This is called when a citizen submits a complaint.
    Every GO connected to the dashboard will see the new complaint in real-time.
    """
    channel_layer = get_channel_layer()
    go_group_name = 'government_officials'
    
    # Prepare complaint data for broadcast
    complaint_data = {
        'id': complaint.id,
        'title': complaint.title,
        'description': complaint.description,
        'category': complaint.category,
        'severity_score': str(complaint.severity_score),
        'latitude': str(complaint.latitude),
        'longitude': str(complaint.longitude),
        'image_url': complaint.image.url if complaint.image else '',
        'created_at': complaint.created_at.isoformat(),
        'status': complaint.status,
    }
    
    # Send to all GOs in the group
    async_to_sync(channel_layer.group_send)(
        go_group_name,
        {
            'type': 'broadcast_new_complaint', # Maps to consumer method
            'complaint_data': complaint_data,
        }
    )
    
    print(f"📢 Complaint #{complaint.id} broadcasted to all GOs")


def broadcast_complaint_update(complaint):
    """
    Broadcast complaint status update to all GOs.
    
    Called when GO updates complaint status (Pending → In Progress → Resolved).
    """
    channel_layer = get_channel_layer()
    go_group_name = 'government_officials'
    
    async_to_sync(channel_layer.group_send)(
        go_group_name,
        {
            'type': 'broadcast_complaint_update',
            'complaint_id': complaint.id,
            'status': complaint.status,
            'timestamp': timezone.now().isoformat(),
        }
    )
    
    print(f"🔄 Complaint #{complaint.id} status updated and broadcasted")


def broadcast_dashboard_metrics():
    """
    Broadcast real-time dashboard metrics to all GOs.
    
    Shows: total complaints, pending, in progress, resolved counts.
    """
    from .models import Complaint
    
    channel_layer = get_channel_layer()
    go_group_name = 'government_officials'
    
    # Calculate metrics
    total = Complaint.objects.count()
    pending = Complaint.objects.filter(status='P').count()
    in_progress = Complaint.objects.filter(status='I').count()
    resolved = Complaint.objects.filter(status='R').count()
    
    async_to_sync(channel_layer.group_send)(
        go_group_name,
        {
            'type': 'broadcast_dashboard_update',
            'total_complaints': total,
            'pending': pending,
            'in_progress': in_progress,
            'resolved': resolved,
            'timestamp': timezone.now().isoformat(),
        }
    )
    
    print(f"📊 Dashboard metrics broadcasted - Total: {total}, Pending: {pending}, In Progress: {in_progress}, Resolved: {resolved}")
