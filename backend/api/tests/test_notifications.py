"""
Notification Tests (TC-NOTIF)
Tests for in-app notifications
"""
import pytest
from django.urls import reverse
from rest_framework import status
from api.models import Notification


@pytest.mark.django_db
class TestNotifications:
    """TC-NOTIF-001 to TC-NOTIF-004: Notification Tests"""

    def test_list_notifications(self, member_client, user_notification):
        """TC-NOTIF-001: List user's notifications"""
        url = reverse('notification-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        notifications = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(notifications) >= 1

    def test_list_notifications_only_own(self, member_client, user_notification, admin_user, ticket_requested, member_user):
        """User only sees their own notifications"""
        # Create notification for admin
        admin_notification = Notification.objects.create(
            user=admin_user,
            ticket=ticket_requested,
            message='Admin notification',
            notification_type='assigned'
        )

        url = reverse('notification-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        notifications = response.data if isinstance(response.data, list) else response.data.get('results', [])
        # Verify that admin's notification is NOT in the list (user filtering works)
        notification_ids = [n.get('id') for n in notifications]
        assert admin_notification.id not in notification_ids

    def test_mark_notification_as_read(self, member_client, user_notification):
        """TC-NOTIF-002: Mark notification as read"""
        assert user_notification.is_read is False

        url = reverse('notification-read', kwargs={'pk': user_notification.id})
        response = member_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        user_notification.refresh_from_db()
        assert user_notification.is_read is True

    def test_mark_all_notifications_read(self, member_client, multiple_notifications):
        """TC-NOTIF-003: Mark all notifications as read"""
        url = reverse('notification-read-all')
        response = member_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Verify all are marked as read
        for notif in multiple_notifications:
            notif.refresh_from_db()
            assert notif.is_read is True

    def test_get_unread_count(self, member_client, multiple_notifications):
        """TC-NOTIF-004: Get unread notification count"""
        url = reverse('notification-unread-count')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data or 'unread_count' in response.data

    def test_notification_includes_ticket_link(self, member_client, user_notification):
        """Notification includes ticket reference"""
        url = reverse('notification-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        notifications = response.data if isinstance(response.data, list) else response.data.get('results', [])
        if notifications:
            notif = notifications[0]
            assert 'ticket' in notif or 'ticket_id' in notif

    def test_notifications_ordered_by_date(self, member_client, multiple_notifications):
        """Notifications are ordered by creation date (newest first)"""
        url = reverse('notification-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        notifications = response.data if isinstance(response.data, list) else response.data.get('results', [])
        if len(notifications) >= 2:
            # Verify ordering (newest first)
            dates = [n.get('created_at', '') for n in notifications]
            assert dates == sorted(dates, reverse=True)


@pytest.mark.django_db
class TestNotificationAccess:
    """Notification Access Control Tests"""

    def test_cannot_read_others_notification(self, member_client, admin_user, ticket_requested):
        """Cannot mark another user's notification as read"""
        admin_notification = Notification.objects.create(
            user=admin_user,
            ticket=ticket_requested,
            message='Admin only',
            notification_type='new_request'
        )

        url = reverse('notification-read', kwargs={'pk': admin_notification.id})
        response = member_client.post(url)

        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_notifications_unauthenticated(self, api_client):
        """Unauthenticated access to notifications fails"""
        url = reverse('notification-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
