from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RegisterView, MeView, UserListView, CustomTokenObtainPairView,
    TicketViewSet, AttachmentDeleteView,
    NotificationViewSet, UserManagementViewSet,
    DashboardView, MyTasksView, TeamOverviewView, OverdueTicketsView,
    ActivityLogListView
)

router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'users/manage', UserManagementViewSet, basename='user-management')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # Auth endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='me'),

    # Users
    path('users/', UserListView.as_view(), name='user-list'),

    # Attachments
    path('attachments/<int:pk>/', AttachmentDeleteView.as_view(), name='attachment-delete'),

    # Dashboard
    path('dashboard/stats/', DashboardView.as_view(), name='dashboard-stats'),
    path('dashboard/my-tasks/', MyTasksView.as_view(), name='my-tasks'),
    path('dashboard/team-overview/', TeamOverviewView.as_view(), name='team-overview'),
    path('dashboard/overdue/', OverdueTicketsView.as_view(), name='overdue-tickets'),

    # Activity logs
    path('activities/', ActivityLogListView.as_view(), name='activity-list'),
]
