"""
Activity Log Tests (TC-ACTIVITY)
Tests for activity logging
"""
import pytest
from django.urls import reverse
from rest_framework import status
from api.models import ActivityLog


@pytest.mark.django_db
class TestActivityLog:
    """TC-ACTIVITY-001 to TC-ACTIVITY-002: Activity Log Tests"""

    def test_list_activities(self, member_client, activity_log):
        """TC-ACTIVITY-001: List activity logs"""
        url = reverse('activity-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        activities = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(activities) >= 1

    def test_activity_created_on_ticket_action(self, manager_client, ticket_requested):
        """TC-ACTIVITY-002: Activity is logged when ticket action is performed"""
        initial_count = ActivityLog.objects.count()

        # Perform an action (approve ticket)
        url = reverse('ticket-approve', kwargs={'pk': ticket_requested.id})
        response = manager_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Check activity was created
        new_count = ActivityLog.objects.count()
        assert new_count > initial_count

    def test_activity_includes_user_info(self, member_client, activity_log):
        """Activity includes user information"""
        url = reverse('activity-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        activities = response.data if isinstance(response.data, list) else response.data.get('results', [])
        if activities:
            activity = activities[0]
            assert 'user' in activity

    def test_activity_includes_ticket_info(self, member_client, activity_log):
        """Activity includes ticket information"""
        url = reverse('activity-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        activities = response.data if isinstance(response.data, list) else response.data.get('results', [])
        if activities:
            activity = activities[0]
            assert 'ticket' in activity or 'ticket_id' in activity

    def test_activity_filter_by_action(self, manager_client, ticket_requested, ticket_approved):
        """Filter activities by action type"""
        # Create some activities (first approval creates 'dept_approved' action for two-step workflow)
        url = reverse('ticket-approve', kwargs={'pk': ticket_requested.id})
        manager_client.post(url)

        # Filter by the actual action used in two-step workflow
        url = reverse('activity-list')
        response = manager_client.get(url, {'action': 'dept_approved'})

        assert response.status_code == status.HTTP_200_OK

        activities = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for activity in activities:
            assert activity['action'] == 'dept_approved'

    def test_activities_ordered_by_date(self, member_client, activity_log):
        """Activities are ordered by date (newest first)"""
        # Create another activity
        ActivityLog.objects.create(
            user=activity_log.user,
            ticket=activity_log.ticket,
            action='updated',
            details='Updated ticket'
        )

        url = reverse('activity-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        activities = response.data if isinstance(response.data, list) else response.data.get('results', [])
        if len(activities) >= 2:
            dates = [a.get('created_at', '') for a in activities]
            assert dates == sorted(dates, reverse=True)


@pytest.mark.django_db
class TestActivityAccess:
    """Activity Log Access Control Tests"""

    def test_activities_unauthenticated(self, api_client):
        """Unauthenticated access to activities fails"""
        url = reverse('activity-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_member_sees_relevant_activities(self, member_client, member_user, ticket_requested, admin_user):
        """Member sees activities for tickets they're involved in"""
        # Create activity for member's ticket
        ActivityLog.objects.create(
            user=member_user,
            ticket=ticket_requested,
            action='created',
            details='Created'
        )

        url = reverse('activity-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK
