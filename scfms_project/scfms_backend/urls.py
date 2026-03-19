from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from complaints.views import AIAnalyzeView
from complaints.debug_views import DebugComplaintsView, DebugTokenView


# --- View Imports ---
from complaints.views import (
    landing_page_view,
    pc_login_view,
    pc_register_view_html,
    pc_dashboard_view,
    go_login_view,
    go_register_view_html,
    go_dashboard_view,
    complaint_form_view,

    # API views
    ComplaintViewSet,
    PCRedistrationView,
    PCLoginView,
    GOLoginView,
    GOComplaintViewSet,
    NotificationListView,
    AnalyticsAPIView,
    GORegistrationView,
    
    # Department Routing Views
    DepartmentListView,
    DepartmentAssignmentListView,
    DepartmentAssignmentDetailView,
    ComplaintRoutingStatusView,

    # Advanced Analytics (Feature #2)
    AnalyticsDetailedView,
    HeatmapDataView,

    # Duplicate Detection (Feature #3)
    SimilarComplaintsView,
    MarkDuplicateView,

    # Timeline (Feature #4)
    TimelineView,

    # Report Generation (Feature #4b)
    GenerateReportView,

    # Chatbot (Feature #5)
    ChatbotView,
)

# Routers
router = DefaultRouter()
router.register(r'complaints', ComplaintViewSet, basename='complaints')

govt_router = DefaultRouter()
govt_router.register(r'complaints', GOComplaintViewSet, basename='govt-complaints')


urlpatterns = [

    # --- Admin ---
    path('admin/', admin.site.urls),

    # --- Landing Page ---
    path('', landing_page_view, name='landing-page'),

    # --- PUBLIC PORTAL (NO LOGIN REQUIRED) ---
    path('public/', pc_dashboard_view, name='pc-dashboard'),

    # Complaint form
    path('report/', complaint_form_view, name='citizen-report-form'),

    # Login/Register pages (UI)
    path('login/', pc_login_view, name='pc-login-html'),
    path('register/', pc_register_view_html, name='pc-register-html'),

    # --- GOVERNMENT PORTAL ---
    path('go-login/', go_login_view, name='go-login-html'),
    path('go-register/', go_register_view_html, name='go-register-html'),
    path('go-dashboard/', go_dashboard_view, name='go-dashboard'),
    path('dashboard/', go_dashboard_view, name='go-dashboard-alt'),  # Backwards compatibility

    # --- PUBLIC API ROUTES ---
    path('api/auth/register/', PCRedistrationView.as_view(), name='pc-register-api'),
    path('api/auth/login/', PCLoginView.as_view(), name='pc-login-api'),
    path('api/notifications/', NotificationListView.as_view(), name='pc-notifications'),
    path('api/', include(router.urls)),

    # --- GOVERNMENT API ROUTES ---
    path('api/govt/login/', GOLoginView.as_view(), name='go-login-api'),
    path('api/govt/register/', GORegistrationView.as_view(), name='go-register-api'),
    path('api/govt/analytics/', AnalyticsAPIView.as_view(), name='govt-analytics'),
    path('api/govt/', include(govt_router.urls)),

    # --- AI Analysis Endpoint ---
    path("api/ai/analyze/", AIAnalyzeView.as_view(), name="ai-analyze"),
    
    # --- DEBUG ENDPOINTS (Remove in production) ---
    path('api/debug/complaints/', DebugComplaintsView.as_view(), name='debug-complaints'),
    path('api/debug/token/', DebugTokenView.as_view(), name='debug-token'),
    
    # --- DEPARTMENT ROUTING ENDPOINTS ---
    path('api/departments/', DepartmentListView.as_view(), name='dept-list'),
    path('api/assignments/<int:pk>/', DepartmentAssignmentDetailView.as_view(), name='assignment-detail'),
    path('api/complaints/<int:complaint_id>/routing-status/', ComplaintRoutingStatusView.as_view(), name='routing-status'),
    path('api/complaints/<int:complaint_id>/assignments/', DepartmentAssignmentListView.as_view(), name='complaint-assignments'),

    # --- ADVANCED ANALYTICS ENDPOINTS (Feature #2) ---
    path('api/analytics/detailed/', AnalyticsDetailedView.as_view(), name='analytics-detailed'),
    path('api/analytics/heatmap/', HeatmapDataView.as_view(), name='analytics-heatmap'),

    # --- DUPLICATE DETECTION ENDPOINTS (Feature #3) ---
    path('api/complaints/similar/', SimilarComplaintsView.as_view(), name='similar-complaints'),
    path('api/complaints/mark-duplicate/', MarkDuplicateView.as_view(), name='mark-duplicate'),

    # --- TIMELINE ENDPOINT (Feature #4) ---
    path('api/complaints/<int:complaint_id>/timeline/', TimelineView.as_view(), name='complaint-timeline'),

    # --- REPORT GENERATION ENDPOINT (Feature #4b) ---
    path('api/reports/generate/', GenerateReportView.as_view(), name='generate-report'),

    # --- CHATBOT ENDPOINT (Feature #5) ---
    path('api/chatbot/', ChatbotView.as_view(), name='chatbot'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
