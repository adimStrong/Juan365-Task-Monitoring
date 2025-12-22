"""
URL configuration for Telegram notifications
"""
from django.urls import path
from . import views

urlpatterns = [
    # Telegram connection endpoints (authenticated)
    path('connect/', views.generate_connection_code, name='telegram-connect'),
    path('status/', views.connection_status, name='telegram-status'),
    path('disconnect/', views.disconnect_telegram, name='telegram-disconnect'),
    path('test/', views.test_notification, name='telegram-test'),
    path('preferences/', views.notification_preferences, name='telegram-preferences'),
    path('admin-link/', views.admin_link_telegram, name='telegram-admin-link'),

    # Telegram webhook (unauthenticated - called by Telegram)
    path('webhook/', views.telegram_webhook, name='telegram-webhook'),
]
