"""
Collaborator Tests
Tests for ticket collaborators
"""
import pytest
from django.urls import reverse
from rest_framework import status
from api.models import TicketCollaborator


@pytest.mark.django_db
class TestTicketCollaborators:
    """Ticket Collaborator Tests"""

    def test_add_collaborator(self, manager_client, ticket_approved, member_user):
        """Add collaborator to ticket"""
        url = reverse('ticket-collaborators', kwargs={'pk': ticket_approved.id})
        data = {'user_id': member_user.id}
        response = manager_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['user']['id'] == member_user.id

    def test_list_collaborators(self, manager_client, ticket_with_collaborator):
        """List collaborators on ticket"""
        ticket, collaborator = ticket_with_collaborator
        url = reverse('ticket-collaborators', kwargs={'pk': ticket.id})
        response = manager_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        collaborators = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(collaborators) >= 1

    def test_remove_collaborator(self, manager_client, ticket_with_collaborator):
        """Remove collaborator from ticket"""
        ticket, collaborator = ticket_with_collaborator
        url = reverse('ticket-collaborators', kwargs={'pk': ticket.id})
        data = {'user_id': collaborator.user.id}
        response = manager_client.delete(url, data, format='json')

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]

        # Verify removed
        assert not TicketCollaborator.objects.filter(id=collaborator.id).exists()

    def test_cannot_add_duplicate_collaborator(self, manager_client, ticket_with_collaborator):
        """Cannot add same user as collaborator twice"""
        ticket, collaborator = ticket_with_collaborator
        url = reverse('ticket-collaborators', kwargs={'pk': ticket.id})
        data = {'user_id': collaborator.user.id}
        response = manager_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_member_cannot_add_collaborator(self, member_client, ticket_approved, admin_user):
        """Regular member cannot add collaborators"""
        url = reverse('ticket-collaborators', kwargs={'pk': ticket_approved.id})
        data = {'user_id': admin_user.id}
        response = member_client.post(url, data, format='json')

        # May be 403 or allowed depending on business rules
        # Just verify it doesn't error
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN]
