from django.shortcuts import render, redirect
from django.conf import settings 
from django.db.models import Count, Avg, F
from django.contrib.auth import authenticate, get_user_model
from django.http import JsonResponse

import os
import google.generativeai as genai

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone


# DRF Imports
from rest_framework import generics, viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny # Corrected import line


# Project Imports
from .serializers import (
    PublicCitizenRegistrationSerializer, 
    ComplaintRegistrationSerializer, 
    NotificationSerializer,
    GORegistrationSerializer
)
from .permissions import IsPublicCitizen, IsGovernmentOfficial
from .models import Complaint, Notification # Removed redundant import (GovernmentWhitelist is implicitly used in GORegistrationSerializer)
from .utils import create_notification, broadcast_complaint_to_gos, broadcast_complaint_update, broadcast_dashboard_metrics
from .ai_service import classify_image_category, generate_description, calculate_severity_score 

User = get_user_model()

# --- HTML TEMPLATE VIEWS (UI) ---

def landing_page_view(request):
    """Serves the main landing page with slogans and navigation choices."""
    return render(request, 'landing_page.html')

def pc_login_view(request):
    """Public Citizen Login Page"""
    if request.user.is_authenticated and request.user.role == 'PC':
        return redirect('citizen-report-form')
    return render(request, 'auth_form.html', {'form_type': 'pc_login'})

def pc_register_view_html(request):
    """Public Citizen Registration Page"""
    if request.user.is_authenticated and request.user.role == 'PC':
        return redirect('citizen-report-form')
    return render(request, 'auth_form.html', {'form_type': 'pc_register'})


def pc_dashboard_view(request):
    return render(request, 'pc_dashboard.html')






def go_login_view(request):
    """Government Official Login Form"""
    return render(request, 'auth_form.html', {'form_type': 'go_login'})

def go_register_view_html(request):
    """Government Official Registration Form"""
    return render(request, 'auth_form.html', {'form_type': 'go_register'})


def complaint_form_view(request):
    """Serves the main complaint submission form. Token validation happens at API level."""
    # For HTML view, we just serve the form. Token will be validated when submitting
    return render(request, 'citizen_register.html')

def go_dashboard_view(request):
    """Serves the Government Official Dashboard HTML."""
    # NOTE: Add auth check here for production (omitted for cleaner presentation focus)
    return render(request, 'go_dashboard.html')


# --- 1. PUBLIC CITIZEN AUTH & API VIEWS ---

# inside complaints/views.py - replace the PCRedistrationView and PCLoginView definitions

@method_decorator(csrf_exempt, name='dispatch')
class PCRedistrationView(generics.CreateAPIView):
    """
    POST /api/auth/register/ - Public Citizen Registration API
    """
    queryset = User.objects.all()
    serializer_class = PublicCitizenRegistrationSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # create user using serializer
        user = serializer.save()

        # Auto-create auth token
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "message": "Registration successful",
            "token": token.key,
            "user_id": user.id,
            "email": user.email,
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class PCLoginView(APIView):
    """
    POST /api/auth/login/ - Public Citizen Login API
    """
    permission_classes = (AllowAny,)

    def post(self, request, format=None):
        try:
            email = request.data.get("email")
            password = request.data.get("password")

            if not email or not password:
                return Response({'error': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

            # Find user by email and ensure role PC
            try:
                user = User.objects.get(email=email, role='PC')
            except User.DoesNotExist:
                return Response({'error': 'Invalid Credentials.'}, status=status.HTTP_400_BAD_REQUEST)

            if not user.check_password(password):
                return Response({'error': 'Invalid Credentials.'}, status=status.HTTP_400_BAD_REQUEST)

            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'user_id': user.pk, 'email': user.email}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)




class ComplaintViewSet(viewsets.ModelViewSet):
    """ Handles POST /api/complaints/register/ and GET /api/complaints/my-history/ """
    queryset = Complaint.objects.all()
    serializer_class = ComplaintRegistrationSerializer

    def get_permissions(self):
        if self.action == 'create' or self.action == 'list':
            self.permission_classes = [IsPublicCitizen]
        else:
            self.permission_classes = [IsAuthenticated] 
            
        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Saves instance and gets image path for AI
        complaint = serializer.save(user=request.user, status='P') 
        image_relative_path = complaint.image.name
        image_full_path = settings.MEDIA_ROOT / image_relative_path
        
        # AI PIPELINE EXECUTION
        category_code = classify_image_category(image_full_path)
        severity_score = calculate_severity_score(category_code)
        title, description = generate_description(image_full_path, category_code)
        
        # Populate and Final Save
        complaint.title = title
        complaint.description = description
        complaint.severity_score = severity_score
        complaint.category = category_code
        complaint.save()

        # === ROUTE TO DEPARTMENT ===
        from .department_routing import DepartmentRoutingService
        try:
            DepartmentRoutingService.route_complaint(complaint)
            print(f"✅ Complaint #{complaint.id} routed to department")
        except Exception as e:
            print(f"⚠️  Department routing failed: {e}")

        # === 🚨 BROADCAST TO ALL GOS VIA WEBSOCKET ===
        try:
            broadcast_complaint_to_gos(complaint)
        except Exception as e:
            print(f"⚠️  WebSocket broadcast failed: {e}")

        headers = self.get_success_headers(serializer.data)
        return Response(self.get_serializer(complaint).data, status=status.HTTP_201_CREATED, headers=headers)
    
    def get_queryset(self):
        if self.action == 'list' and self.request.user.role == 'PC':
            return self.queryset.filter(user=self.request.user).order_by('-created_at')
        return self.queryset.none() 


class NotificationListView(generics.ListAPIView):
    """ GET /api/notifications/ - PC view own notifications. """
    serializer_class = NotificationSerializer
    permission_classes = [IsPublicCitizen]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


# --- 4. GOVERNMENT OFFICIAL AUTH & API VIEWS ---

class GORegistrationView(generics.CreateAPIView):
    """ POST /api/govt/register/ - GO Registration (Creates inactive account). """
    queryset = User.objects.all()
    serializer_class = GORegistrationSerializer
    permission_classes = (AllowAny,)


class GOLoginView(APIView):
    """ POST /api/govt/login/ - Government Official Login API """
    permission_classes = (AllowAny,)

    def post(self, request, format=None):
        email = request.data.get("email")
        password = request.data.get("password")
        govt_id = request.data.get("govt_id")
        
        print(f"🔐 GO Login attempt: email={email}, govt_id={govt_id}")
        
        try:
            # Try to get user by email first (primary method)
            if email:
                user = User.objects.get(email=email)
            elif govt_id:
                user = User.objects.get(govt_id=govt_id)
            else:
                return Response({'error': 'Email or Government ID required.'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            print(f"❌ User not found: email={email}, govt_id={govt_id}")
            return Response({'error': 'Invalid credentials or user not found.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check user role
        if user.role != 'GO':
            print(f"❌ User role is not GO: {user.role}")
            return Response({'error': 'This account is not a Government Official account.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is active
        if not user.is_active:
            print(f"❌ User account inactive: {user.email}")
            return Response({'error': 'Account has been deactivated.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check password
        if not user.check_password(password):
            print(f"❌ Invalid password for user: {user.email}")
            return Response({'error': 'Invalid email/password combination.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure is_verified is True (auto-verify if needed)
        if not user.is_verified:
            print(f"⚠️  Auto-verifying user: {user.email}")
            user.is_verified = True
            user.save()
        
        # Create or get token
        token, created = Token.objects.get_or_create(user=user)
        print(f"✅ GO Login successful: {user.email}, token={'created' if created else 'existing'}")
        
        return Response({
            'token': token.key,
            'go_token': token.key,  # For backwards compatibility
            'user_id': user.pk,
            'email': user.email,
            'govt_id': user.govt_id,
            'role': user.role
        }, status=status.HTTP_200_OK)
    

class GOComplaintViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet): 
    """ Handles GO list, filter, sort (by severity), and status update. """
    queryset = Complaint.objects.all().order_by('-severity_score', '-created_at')
    permission_classes = [IsGovernmentOfficial]

    def get_serializer_class(self):
        """Use different serializer for list vs retrieve"""
        from .serializers import ComplaintListSerializer, ComplaintRegistrationSerializer
        if self.action == 'list' or self.action == 'retrieve':
            return ComplaintListSerializer
        return ComplaintRegistrationSerializer

    def list(self, request, *args, **kwargs):
        print(f"🔐 GOComplaintViewSet.list() called")
        print(f"   User: {request.user}")
        print(f"   User Role: {request.user.role if hasattr(request.user, 'role') else 'N/A'}")
        print(f"   Authenticated: {request.user.is_authenticated}")
        print(f"   Total complaints in DB: {Complaint.objects.count()}")
        
        queryset = self.get_queryset()
        
        status_filter = request.query_params.get('status')
        category_filter = request.query_params.get('category')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        if category_filter:
            queryset = queryset.filter(category=category_filter.upper())

        print(f"   Complaints after filter: {queryset.count()}")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        print(f"   Returning {len(serializer.data)} complaints")
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        new_status = request.data.get('status')

        valid_statuses = [choice[0] for choice in Complaint.STATUS_CHOICES]
        if new_status and new_status in valid_statuses:
            instance.status = new_status
            instance.save()
            
            # NOTIFICATION LOGIC
            citizen = instance.user
            if new_status == 'I':
                message = f"Your complaint '{instance.title}' has been **ACCEPTED** and is now in progress."
            elif new_status == 'R':
                message = f"Your complaint '{instance.title}' has been **RESOLVED** by a Government Official."
            else:
                message = f"The status of your complaint '{instance.title}' has been updated."

            create_notification(user=citizen, message=message, complaint=instance)
            
            # === 🔄 BROADCAST STATUS UPDATE TO ALL GOs ===
            try:
                broadcast_complaint_update(instance)
                broadcast_dashboard_metrics()
            except Exception as e:
                print(f"⚠️  WebSocket broadcast failed: {e}")
            
            return Response({'status': f'Complaint status updated to {instance.get_status_display()}'})
        
        return Response({'error': 'Invalid status provided.'}, status=status.HTTP_400_BAD_REQUEST)
    

class AnalyticsAPIView(APIView):
    """ Provides aggregated data for dashboard charts and metrics. """
    permission_classes = [IsAuthenticated, IsGovernmentOfficial] 

    def get(self, request, format=None):
        status_counts = Complaint.objects.values('status').annotate(count=Count('id')).order_by('status')
        category_counts = Complaint.objects.values('category').annotate(count=Count('id')).order_by('category')

        high_priority_count = Complaint.objects.filter(severity_score__gte=70).count()
        total_resolved_count = Complaint.objects.filter(status='R').count()
        total_complaints = Complaint.objects.count()

        data = {
            'status_distribution': status_counts,
            'category_distribution': category_counts,
            'metrics': {
                'total_complaints': total_complaints,
                'high_priority_count': high_priority_count,
                'total_resolved_count': total_resolved_count,
            }
        }
        return Response(data)
    
@method_decorator(csrf_exempt, name='dispatch')
class AIAnalyzeView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        try:
            image = request.FILES.get('image')
            if not image:
                return Response({"error": "Image is required"}, status=400)

            from .ai_service import classify_image_category, generate_description, calculate_severity_score

            # Save temporarily
            temp_path = settings.MEDIA_ROOT / "temp_ai.jpg"
            with open(temp_path, "wb") as f:
                for chunk in image.chunks():
                    f.write(chunk)

            print(f"📸 Image saved to: {temp_path}")

            # === AI Classification ===
            department_code = classify_image_category(temp_path)
            print(f"🏷️ Department code: {department_code}")
            
            severity_score = calculate_severity_score(department_code)
            print(f"⚠️ Severity score: {severity_score}")
            
            title, description = generate_description(temp_path, department_code)
            print(f"✅ Title: {title}")
            print(f"✅ Description: {description}")

            # Convert dept code → full department name
            department_map = {
                "RO": "Public Works Department (PWD)",
                "GA": "Sanitation Department",
                "UT": "Water / Electricity Utilities",
                "PB": "Police / Behavioral Issues",
                "OT": "General Issues"
            }

            department = department_map.get(department_code, "General")

            return Response({
                "department": department,
                "severity_score": severity_score,
                "title": title,
                "description": description
            })
            
        except Exception as e:
            print(f"❌ AIAnalyzeView error: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                "error": str(e),
                "title": "Analysis Failed",
                "description": "Unable to analyze the image",
                "department": "General",
                "severity_score": 50
            }, status=500)


@csrf_exempt
def ai_analyze_view(request):
    import google.generativeai as genai
    from django.http import JsonResponse
    from django.conf import settings
    
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    if "image" not in request.FILES:
        return JsonResponse({"error": "No image uploaded"}, status=400)

    image_file = request.FILES["image"]

    # LOAD API KEY
    genai.configure(api_key=settings.GEMINI_API_KEY)

    # Read image bytes
    image_bytes = image_file.read()

    # GEMINI MODEL
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = """
    You are an AI civic issue detector.
    Analyze the image and return ONLY valid JSON:

    {
      "department": "...",
      "title": "...",
      "description": "...",
      "severity_score": 0-100
    }

    Department must be one of:
    - Roads
    - Water
    - Electricity
    - Garbage
    - Public Safety
    - Other

    Title: max 7 words  
    Description: max 40 words  
    """

    try:
        response = model.generate_content([
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"image": image_bytes}
                ]
            }
        ])

        import json
        result = json.loads(response.text)

        return JsonResponse({
            "department": result.get("department", "Other"),
            "title": result.get("title", "Issue detected"),
            "description": result.get("description", "No description generated"),
            "severity_score": result.get("severity_score", 40),
        })

    except Exception as e:
        print("GEMINI ERROR:", e)
        return JsonResponse({"error": "AI processing failed"}, status=500)


# ============================================================
#             DEPARTMENT ROUTING API VIEWS
# ============================================================

class DepartmentListView(generics.ListAPIView):
    """GET /api/departments/ - List all active departments"""
    from .models import Department
    from .serializers import DepartmentSerializer
    
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]


class DepartmentAssignmentListView(generics.ListAPIView):
    """GET /api/departments/<complaint_id>/assignments/ - View assignments for a complaint"""
    from .models import DepartmentAssignment
    from .serializers import DepartmentAssignmentSerializer
    
    serializer_class = DepartmentAssignmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        complaint_id = self.kwargs.get('complaint_id')
        return DepartmentAssignment.objects.filter(complaint_id=complaint_id)


class DepartmentAssignmentDetailView(generics.RetrieveUpdateAPIView):
    """GET/PUT /api/assignments/<id>/ - View/update assignment details"""
    from .models import DepartmentAssignment
    from .serializers import DepartmentAssignmentSerializer
    
    queryset = DepartmentAssignment.objects.all()
    serializer_class = DepartmentAssignmentSerializer
    permission_classes = [IsAuthenticated, IsGovernmentOfficial]
    
    def update(self, request, *args, **kwargs):
        """Update assignment status and send notifications"""
        from .department_routing import DepartmentAssignmentService
        
        assignment = self.get_object()
        status_update = request.data.get('status')
        notes = request.data.get('notes', '')
        
        valid_statuses = [choice[0] for choice in assignment.STATUS_CHOICES]
        if status_update and status_update in valid_statuses:
            if status_update == 'ACKNOWLEDGED':
                DepartmentAssignmentService.acknowledge_assignment(assignment)
            elif status_update == 'IN_PROGRESS':
                DepartmentAssignmentService.mark_in_progress(assignment, notes)
            elif status_update == 'RESOLVED':
                DepartmentAssignmentService.mark_resolved(assignment, notes)
            
            return Response({
                'status': 'Assignment updated successfully',
                'assignment': self.get_serializer(assignment).data
            })
        
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)


class ComplaintRoutingStatusView(APIView):
    """GET /api/complaints/<id>/routing-status/ - View routing status of a complaint"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, complaint_id):
        from .department_routing import DepartmentAssignmentService
        
        try:
            complaint = Complaint.objects.get(id=complaint_id)
            routing_status = DepartmentAssignmentService.get_assignment_status(complaint)
            
            return Response({
                'complaint_id': complaint.id,
                'title': complaint.title,
                'routing_status': routing_status
            })
        except Complaint.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


# ============================================================
#            ADVANCED ANALYTICS VIEWS  (Feature #2)
# ============================================================

class AnalyticsDetailedView(APIView):
    """
    GET /api/analytics/detailed/
    Returns comprehensive analytics:
      - Key metrics (totals, resolution rate, avg resolution days, high priority)
      - Department performance
      - 30-day complaint trends
      - Category distribution
      - Status distribution
    """
    permission_classes = [IsAuthenticated, IsGovernmentOfficial]

    def get(self, request):
        from datetime import timedelta
        from .models import Department, DepartmentAssignment

        today = timezone.now().date()
        month_ago = today - timedelta(days=30)

        # ── Key Metrics ────────────────────────────────────
        total_complaints = Complaint.objects.count()
        resolved_complaints = Complaint.objects.filter(status='R').count()
        high_priority = Complaint.objects.filter(severity_score__gte=70).count()

        # Average resolution time (in days) for resolved complaints
        resolved_qs = Complaint.objects.filter(
            status='R',
            department_assignments__resolved_at__isnull=False
        ).annotate(
            resolution_secs=Avg(
                F('department_assignments__resolved_at') - F('created_at')
            )
        )
        total_secs = 0
        count_with_time = 0
        for c in resolved_qs:
            if c.resolution_secs:
                total_secs += c.resolution_secs.total_seconds()
                count_with_time += 1
        avg_resolution_days = round(total_secs / count_with_time / 86400, 1) if count_with_time else 0

        # ── Department Performance ──────────────────────────
        dept_performance = []
        for dept in Department.objects.filter(is_active=True):
            assignments = DepartmentAssignment.objects.filter(department=dept)
            resolved = assignments.filter(status='RESOLVED').count()
            total = assignments.count()

            # Average resolution time for this department
            avg_days = 0
            if total > 0:
                timed = assignments.filter(resolved_at__isnull=False)
                if timed.exists():
                    secs_list = [
                        (a.resolved_at - a.assigned_at).total_seconds()
                        for a in timed
                        if a.resolved_at and a.assigned_at
                    ]
                    if secs_list:
                        avg_days = round(sum(secs_list) / len(secs_list) / 86400, 1)

            dept_performance.append({
                'department': dept.department_name,
                'category': dept.category,
                'total_complaints': total,
                'resolved': resolved,
                'resolved_percentage': round(resolved / total * 100, 1) if total > 0 else 0,
                'avg_resolution_days': avg_days,
            })

        # ── 30-Day Complaint Trends ─────────────────────────
        daily_counts = {}
        for i in range(30):
            date = month_ago + timedelta(days=i)
            count = Complaint.objects.filter(created_at__date=date).count()
            daily_counts[str(date)] = count

        # ── Category Distribution ───────────────────────────
        category_labels = {
            'RO': 'Roads/Potholes',
            'GA': 'Garbage/Waste',
            'UT': 'Utilities',
            'PB': 'Public Behavior',
            'OT': 'Other',
        }
        cat_qs = Complaint.objects.values('category').annotate(count=Count('id')).order_by('-count')
        categories = [{
            'label': category_labels.get(c['category'], c['category']),
            'value': c['count'],
            'percentage': round(c['count'] / total_complaints * 100, 1) if total_complaints > 0 else 0,
        } for c in cat_qs]

        # ── Status Distribution ─────────────────────────────
        status_labels = {'P': 'Pending', 'I': 'In Progress', 'R': 'Resolved'}
        stat_qs = Complaint.objects.values('status').annotate(count=Count('id'))
        statuses = [{
            'label': status_labels.get(s['status'], s['status']),
            'value': s['count'],
        } for s in stat_qs]

        return Response({
            'key_metrics': {
                'total_complaints': total_complaints,
                'resolved_complaints': resolved_complaints,
                'resolution_rate': round(resolved_complaints / total_complaints * 100, 1) if total_complaints > 0 else 0,
                'high_priority_count': high_priority,
                'avg_resolution_days': avg_resolution_days,
            },
            'department_performance': dept_performance,
            'complaint_trends': daily_counts,
            'category_distribution': categories,
            'status_distribution': statuses,
            'last_updated': str(timezone.now()),
        })


class HeatmapDataView(APIView):
    """
    GET /api/analytics/heatmap/
    Returns lat/lng/intensity points for all complaints (used by Leaflet heatmap).
    """
    permission_classes = [IsAuthenticated, IsGovernmentOfficial]

    def get(self, request):
        complaints = Complaint.objects.values(
            'latitude', 'longitude', 'severity_score', 'category', 'id', 'title'
        )
        heatmap_data = []
        for c in complaints:
            try:
                heatmap_data.append({
                    'lat': float(c['latitude']),
                    'lng': float(c['longitude']),
                    'intensity': float(c['severity_score']) / 100,
                    'category': c['category'],
                    'complaint_id': c['id'],
                    'title': c['title'],
                })
            except (TypeError, ValueError):
                continue  # Skip complaints without valid coordinates

        return Response({
            'points': heatmap_data,
            'center': {'lat': 20.5937, 'lng': 78.9629},  # India centre
            'count': len(heatmap_data),
        })


# ============================================================
#          FEATURE #3: DUPLICATE DETECTION VIEWS
# ============================================================

class SimilarComplaintsView(APIView):
    """
    GET /api/complaints/similar/?text=<complaint title + description>
    Returns complaints that are >= threshold similar to the query text.
    Allowed to unauthenticated users so the warning appears before login.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        text = request.query_params.get('text', '').strip()
        if not text:
            return Response({'error': 'text parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        from .ml_service import DuplicateDetectionService
        similar = DuplicateDetectionService.find_similar_complaints(text)

        results = [
            {
                'id':                   s['complaint'].id,
                'title':                s['complaint'].title,
                'description':          s['complaint'].description[:200],
                'status':               s['complaint'].get_status_display(),
                'category':             s['complaint'].get_category_display(),
                'similarity_percentage': s['similarity_percentage'],
                'created_at':           s['complaint'].created_at.isoformat(),
            }
            for s in similar
        ]
        return Response({'similar_complaints': results, 'count': len(results)})


class MarkDuplicateView(APIView):
    """
    POST /api/complaints/mark-duplicate/
    Body: { "original_complaint_id": <int>, "duplicate_complaint_id": <int> }
    Government Official only.
    """
    permission_classes = [IsAuthenticated, IsGovernmentOfficial]

    def post(self, request):
        original_id  = request.data.get('original_complaint_id')
        duplicate_id = request.data.get('duplicate_complaint_id')

        if not original_id or not duplicate_id:
            return Response(
                {'error': 'Both original_complaint_id and duplicate_complaint_id are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if original_id == duplicate_id:
            return Response(
                {'error': 'A complaint cannot be a duplicate of itself'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .ml_service import DuplicateDetectionService
        success = DuplicateDetectionService.mark_as_duplicate(original_id, duplicate_id)

        if success:
            return Response({'status': f'Complaint #{duplicate_id} marked as duplicate of #{original_id}'})
        return Response({'error': 'Failed to mark as duplicate — check complaint IDs'}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
#          FEATURE #4: COMPLAINT TIMELINE VIEW
# ============================================================

class TimelineView(APIView):
    """
    GET /api/complaints/<id>/timeline/
    Returns an ordered list of events in a complaint's lifecycle.
    Citizens can only view their own complaints; GOs can view all.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, complaint_id):
        from .models import Complaint, DepartmentAssignment
        from django.shortcuts import get_object_or_404

        complaint = get_object_or_404(Complaint, id=complaint_id)

        # Ownership check for public citizens
        if hasattr(request.user, 'role') and request.user.role == 'PC':
            if complaint.user != request.user:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        timeline = []

        # ── Event 1: Complaint Created ───────────────────────────
        timeline.append({
            'action':      'CREATED',
            'icon':        '📝',
            'title':       'Complaint Submitted',
            'description': f'"{complaint.title}" was submitted by {complaint.user.email}.',
            'actor':       complaint.user.email,
            'timestamp':   complaint.created_at.isoformat(),
            'color':       '#6366f1',
        })

        # ── Events from DepartmentAssignments ─────────────────────
        assignments = complaint.department_assignments.select_related('department', 'assigned_by').all()

        for assignment in assignments:
            dept = assignment.department.department_name

            # Assigned
            timeline.append({
                'action':      'ASSIGNED',
                'icon':        '🏢',
                'title':       f'Assigned to {dept}',
                'description': assignment.notes or f'Complaint forwarded to {dept} for resolution.',
                'actor':       assignment.assigned_by.email if assignment.assigned_by else 'System',
                'timestamp':   assignment.assigned_at.isoformat(),
                'color':       '#f59e0b',
            })

            # Acknowledged
            if assignment.acknowledged_at:
                timeline.append({
                    'action':      'ACKNOWLEDGED',
                    'icon':        '👀',
                    'title':       f'{dept} Acknowledged',
                    'description': f'{dept} has received and acknowledged the complaint.',
                    'actor':       assignment.department.department_head_name,
                    'timestamp':   assignment.acknowledged_at.isoformat(),
                    'color':       '#06b6d4',
                })

            # Resolved
            if assignment.resolved_at:
                timeline.append({
                    'action':      'RESOLVED',
                    'icon':        '✅',
                    'title':       'Issue Resolved',
                    'description': assignment.notes or f'{dept} has resolved the complaint.',
                    'actor':       assignment.department.department_head_name,
                    'timestamp':   assignment.resolved_at.isoformat(),
                    'color':       '#10b981',
                })

        # Sort all events chronologically
        timeline.sort(key=lambda e: e['timestamp'])

        # Mark which step is "current" (last non-resolved)
        current_idx = len(timeline) - 1
        for i, ev in enumerate(timeline):
            ev['is_current'] = (i == current_idx)

        return Response({
            'complaint_id':    complaint_id,
            'complaint_title': complaint.title,
            'status':          complaint.get_status_display(),
            'is_duplicate':    complaint.is_duplicate,
            'original_id':     complaint.original_complaint_id,
            'timeline':        timeline,
        })


# ============================================================
#        FEATURE #4: PDF REPORT GENERATION VIEW
# ============================================================

class GenerateReportView(APIView):
    """
    GET /api/reports/generate/?period=<weekly|monthly|quarterly|all>
    Downloads a professional PDF analytics report.
    Government Officials only.
    """
    permission_classes = [IsAuthenticated, IsGovernmentOfficial]

    def get(self, request):
        from django.http import HttpResponse
        from .report_service import ReportService

        period = request.query_params.get('period', 'monthly')
        if period not in ('weekly', 'monthly', 'quarterly', 'all'):
            period = 'monthly'

        generated_by = request.user.email

        try:
            pdf_bytes = ReportService.generate_pdf(
                period=period,
                generated_by=generated_by,
            )
        except Exception as exc:
            logger.error(f"Report generation error: {exc}")
            return Response(
                {'error': f'Failed to generate report: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        filename = f"scfms_report_{period}_{timezone.now().strftime('%Y%m%d')}.pdf"

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)
        return response


# ============================================================
#         FEATURE #5: CHATBOT ASSISTANT VIEW
# ============================================================

class ChatbotView(APIView):
    """
    POST /api/chatbot/
    Body: { "message": "...", "history": [{"role":"user","parts":["..."]}, ...] }
    Returns: { "reply": "..." }
    Accessible to any authenticated user (citizen or GO).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .chatbot_service import ChatbotService

        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'error': 'message is required'}, status=status.HTTP_400_BAD_REQUEST)

        # history: list of {"role": "user" | "model", "parts": ["text"]}
        history = request.data.get('history', [])

        reply = ChatbotService.get_response(
            user_message=message,
            conversation_history=history,
        )

        return Response({'reply': reply})
