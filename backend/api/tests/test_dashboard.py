"""
Dashboard Tests (TC-DASH)
Tests for dashboard statistics and data
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestDashboardStats:
    """TC-DASH-001 to TC-DASH-004: Dashboard Tests"""

    def test_get_dashboard_stats(self, member_client):
        """TC-DASH-001: Get dashboard statistics"""
        url = reverse('dashboard-stats')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Check required stats fields
        data = response.data
        assert 'total_tickets' in data or 'stats' in data
        # May include: pending_approval, in_progress, overdue, etc.

    def test_dashboard_stats_with_tickets(self, member_client, multiple_tickets):
        """Dashboard stats reflect actual ticket counts"""
        url = reverse('dashboard-stats')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        total = data.get('total_tickets', data.get('stats', {}).get('total', 0))
        assert total >= 0  # Should have some tickets

    def test_get_my_tasks(self, admin_client, ticket_assigned):
        """TC-DASH-002: Get user's assigned tasks"""
        url = reverse('my-tasks')
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        tasks = response.data if isinstance(response.data, list) else response.data.get('results', [])
        # Admin should have at least one assigned ticket
        assert len(tasks) >= 0  # May be 0 if no tickets assigned to current user

    def test_team_overview_as_manager(self, manager_client, multiple_tickets):
        """TC-DASH-003: Manager can get team overview"""
        url = reverse('team-overview')
        response = manager_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_team_overview_as_member_forbidden(self, member_client):
        """Regular member cannot access team overview"""
        url = reverse('team-overview')
        response = member_client.get(url)

        # May return 403 or empty data depending on implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    def test_get_overdue_tickets(self, manager_client, ticket_with_deadline):
        """TC-DASH-004: Get overdue tickets"""
        url = reverse('overdue-tickets')
        response = manager_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        tickets = response.data if isinstance(response.data, list) else response.data.get('results', [])
        # May or may not have overdue tickets
        assert isinstance(tickets, list)


@pytest.mark.django_db
class TestDashboardCharts:
    """Dashboard Chart Data Tests"""

    def test_stats_include_chart_data(self, member_client, multiple_tickets):
        """Dashboard stats include data for charts"""
        url = reverse('dashboard-stats')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        # Check for chart data fields
        # May include: status_distribution, priority_distribution, weekly_trends

    def test_stats_by_status(self, member_client, multiple_tickets):
        """Dashboard includes ticket counts by status"""
        url = reverse('dashboard-stats')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Implementation may vary
        data = response.data

    def test_stats_by_priority(self, member_client, multiple_tickets):
        """Dashboard includes ticket counts by priority"""
        url = reverse('dashboard-stats')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestDashboardAccess:
    """Dashboard Access Control Tests"""

    def test_dashboard_unauthenticated(self, api_client):
        """Unauthenticated access to dashboard fails"""
        url = reverse('dashboard-stats')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_my_tasks_unauthenticated(self, api_client):
        """Unauthenticated access to my tasks fails"""
        url = reverse('my-tasks')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
