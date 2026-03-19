# complaints/debug_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Complaint, User, DepartmentAssignment


class DebugComplaintsView(APIView):
    """Debug endpoint to check complaints in database"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            total_complaints = Complaint.objects.count()
            complaints = Complaint.objects.all().values(
                'id', 'title', 'category', 'status', 'severity_score',
                'user__email', 'user__role', 'created_at'
            )
            
            total_users = User.objects.count()
            go_users = User.objects.filter(role='GO').values(
                'id', 'email', 'govt_id', 'is_active', 'role'
            )
            
            assignments = DepartmentAssignment.objects.count()
            
            return Response({
                'total_complaints': total_complaints,
                'complaints': list(complaints),
                'total_users': total_users,
                'government_officials': list(go_users),
                'total_assignments': assignments,
            })
        except Exception as e:
            return Response({
                'error': str(e),
                'type': type(e).__name__
            }, status=500)


class DebugTokenView(APIView):
    """Debug endpoint to check if token auth is working"""
    
    def get(self, request):
        return Response({
            'authenticated': bool(request.user and request.user.is_authenticated),
            'user': str(request.user),
            'user_role': request.user.role if hasattr(request.user, 'role') else 'N/A',
            'user_id': request.user.id if hasattr(request.user, 'id') else 'N/A',
            'token': request.auth,
        })
