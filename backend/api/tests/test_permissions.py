"""
Permission Tests (TC-PERM)
Tests for role-based access control
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestAdminPermissions:
    """Admin Role Permission Tests"""

    def test_admin_can_manage_users(self, admin_client, member_user):
        """Admin has full user management access"""
        url = reverse('user-management-list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_approve_tickets(self, admin_client, ticket_requested):
        """Admin can approve tickets"""
        url = reverse('ticket-approve', kwargs={'pk': ticket_requested.id})
        response = admin_client.post(url)
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_assign_tickets(self, admin_client, ticket_approved, member_user):
        """Admin can assign tickets"""
        url = reverse('ticket-assign', kwargs={'pk': ticket_approved.id})
        data = {'assigned_to': member_user.id}
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_change_roles(self, admin_client, member_user):
        """Admin can change user roles"""
        url = reverse('user-management-change-role', kwargs={'pk': member_user.id})
        response = admin_client.post(url, {'role': 'manager'}, format='json')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestManagerPermissions:
    """Manager Role Permission Tests"""

    def test_manager_can_view_all_tickets(self, manager_client, ticket_requested):
        """Manager can view all tickets"""
        url = reverse('ticket-list')
        response = manager_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_manager_can_approve_tickets(self, manager_client, ticket_requested):
        """Manager can approve tickets"""
        url = reverse('ticket-approve', kwargs={'pk': ticket_requested.id})
        response = manager_client.post(url)
        assert response.status_code == status.HTTP_200_OK

    def test_manager_can_assign_tickets(self, manager_client, ticket_approved, member_user):
        """Manager can assign tickets"""
        url = reverse('ticket-assign', kwargs={'pk': ticket_approved.id})
        data = {'assigned_to': member_user.id}
        response = manager_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_manager_can_view_team_overview(self, manager_client):
        """Manager can view team overview"""
        url = reverse('team-overview')
        response = manager_client.get(url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestMemberPermissions:
    """Member Role Permission Tests"""

    def test_member_can_create_tickets(self, member_client, valid_ticket_data):
        """Member can create tickets"""
        url = reverse('ticket-list')
        response = member_client.post(url, valid_ticket_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_member_cannot_approve_tickets(self, member_client, ticket_requested):
        """Member cannot approve tickets"""
        url = reverse('ticket-approve', kwargs={'pk': ticket_requested.id})
        response = member_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_member_cannot_assign_tickets(self, member_client, ticket_approved, admin_user):
        """Member cannot assign tickets"""
        url = reverse('ticket-assign', kwargs={'pk': ticket_approved.id})
        data = {'assigned_to': admin_user.id}
        response = member_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_member_cannot_manage_users(self, member_client):
        """Member cannot manage users"""
        url = reverse('user-management-list')
        response = member_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_member_can_view_own_tickets(self, member_client, ticket_requested):
        """Member can view their own tickets"""
        url = reverse('ticket-detail', kwargs={'pk': ticket_requested.id})
        response = member_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_member_can_comment_on_tickets(self, member_client, ticket_requested):
        """Member can comment on tickets"""
        url = reverse('ticket-comments', kwargs={'pk': ticket_requested.id})
        data = {'comment': 'Test comment'}
        response = member_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestUnauthenticatedAccess:
    """Unauthenticated Access Tests"""

    def test_unauthenticated_cannot_list_tickets(self, api_client):
        """Unauthenticated user cannot list tickets"""
        url = reverse('ticket-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_create_ticket(self, api_client, valid_ticket_data):
        """Unauthenticated user cannot create tickets"""
        url = reverse('ticket-list')
        response = api_client.post(url, valid_ticket_data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_view_dashboard(self, api_client):
        """Unauthenticated user cannot view dashboard"""
        url = reverse('dashboard-stats')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_view_users(self, api_client):
        """Unauthenticated user cannot view user management"""
        url = reverse('user-management-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTicketOwnership:
    """Ticket Ownership Permission Tests"""

    def test_requester_can_confirm_completion(self, member_client, ticket_completed, member_user):
        """Requester can confirm ticket completion"""
        ticket_completed.requester = member_user
        ticket_completed.save()

        url = reverse('ticket-confirm', kwargs={'pk': ticket_completed.id})
        response = member_client.post(url)
        assert response.status_code == status.HTTP_200_OK

    def test_non_requester_cannot_confirm(self, manager_client, ticket_completed):
        """Non-requester cannot confirm ticket completion"""
        url = reverse('ticket-confirm', kwargs={'pk': ticket_completed.id})
        response = manager_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_assigned_user_can_complete_ticket(self, admin_client, ticket_in_progress):
        """Assigned user can complete ticket"""
        url = reverse('ticket-complete', kwargs={'pk': ticket_in_progress.id})
        response = admin_client.post(url)
        assert response.status_code == status.HTTP_200_OK
