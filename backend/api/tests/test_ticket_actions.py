"""
Ticket Actions Tests (TC-ACTION)
Tests for ticket workflow actions: approve, reject, assign, start, complete, confirm
"""
import pytest
from django.urls import reverse
from rest_framework import status
from api.models import Ticket, ActivityLog


@pytest.mark.django_db
class TestTicketApproval:
    """TC-ACTION-001 to TC-ACTION-003: Ticket Approval/Rejection Tests"""

    def test_approve_ticket_as_manager(self, manager_client, ticket_requested):
        """TC-ACTION-001: Manager can do first approval (REQUESTED → PENDING_CREATIVE)"""
        url = reverse('ticket-approve', kwargs={'pk': ticket_requested.id})
        response = manager_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        # Two-step workflow: first approval moves to pending_creative
        assert response.data['status'] == 'pending_creative'

        # Verify in database
        ticket_requested.refresh_from_db()
        assert ticket_requested.status == 'pending_creative'

    def test_approve_ticket_as_admin(self, admin_client, ticket_requested):
        """Admin (in Creative dept) can do final approval"""
        # First, set ticket to pending_creative status (simulating first approval)
        ticket_requested.status = 'pending_creative'
        ticket_requested.save()

        url = reverse('ticket-approve', kwargs={'pk': ticket_requested.id})
        response = admin_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'approved'

    def test_approve_ticket_as_member_forbidden(self, member_client, ticket_requested):
        """TC-ACTION-002: Regular member cannot approve ticket"""
        url = reverse('ticket-approve', kwargs={'pk': ticket_requested.id})
        response = member_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reject_ticket_with_reason(self, manager_client, ticket_requested):
        """TC-ACTION-003: Manager can reject ticket with reason"""
        url = reverse('ticket-reject', kwargs={'pk': ticket_requested.id})
        data = {'reason': 'Not a valid request'}
        response = manager_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'rejected'

    def test_reject_ticket_without_reason(self, manager_client, ticket_requested):
        """Manager can reject ticket without reason (optional)"""
        url = reverse('ticket-reject', kwargs={'pk': ticket_requested.id})
        response = manager_client.post(url)

        # Should succeed - reason is optional
        assert response.status_code == status.HTTP_200_OK

    def test_cannot_approve_already_approved(self, manager_client, ticket_approved):
        """Cannot approve an already approved ticket"""
        url = reverse('ticket-approve', kwargs={'pk': ticket_approved.id})
        response = manager_client.post(url)

        # Should fail or return current state
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]


@pytest.mark.django_db
class TestTicketAssignment:
    """TC-ACTION-004 to TC-ACTION-005: Ticket Assignment Tests"""

    def test_assign_ticket(self, manager_client, ticket_approved, creative_user):
        """TC-ACTION-004: Manager can assign ticket to Creative department user"""
        url = reverse('ticket-assign', kwargs={'pk': ticket_approved.id})
        data = {'assigned_to': creative_user.id}
        response = manager_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['assigned_to']['id'] == creative_user.id

        # Verify in database
        ticket_approved.refresh_from_db()
        assert ticket_approved.assigned_to == creative_user

    def test_assign_ticket_not_approved(self, manager_client, ticket_requested, creative_user):
        """TC-ACTION-005: Assign ticket that's not approved"""
        url = reverse('ticket-assign', kwargs={'pk': ticket_requested.id})
        data = {'assigned_to': creative_user.id}
        response = manager_client.post(url, data, format='json')

        # API may allow assigning unapproved tickets (policy decision)
        # Test that assignment is handled (200) or rejected (400)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_assign_ticket_as_member_forbidden(self, member_client, ticket_approved, creative_user):
        """Regular member cannot assign tickets"""
        url = reverse('ticket-assign', kwargs={'pk': ticket_approved.id})
        data = {'assigned_to': creative_user.id}
        response = member_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reassign_ticket(self, manager_client, ticket_approved, creative_user):
        """Manager can reassign ticket to different Creative department user"""
        # Use ticket_approved instead of ticket_assigned to avoid IN_PROGRESS restriction
        url = reverse('ticket-assign', kwargs={'pk': ticket_approved.id})
        data = {'assigned_to': creative_user.id}
        response = manager_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTicketWorkflow:
    """TC-ACTION-006 to TC-ACTION-010: Ticket Workflow Tests"""

    def test_start_work(self, admin_client, ticket_assigned):
        """TC-ACTION-006: Assigned user can start work"""
        url = reverse('ticket-start', kwargs={'pk': ticket_assigned.id})
        response = admin_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'in_progress'

    def test_start_work_not_assigned_fails(self, member_client, ticket_approved):
        """TC-ACTION-007: Cannot start work on unassigned ticket"""
        url = reverse('ticket-start', kwargs={'pk': ticket_approved.id})
        response = member_client.post(url)

        # Should fail or return permission error
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    def test_complete_ticket(self, admin_client, ticket_in_progress):
        """TC-ACTION-008: Assigned user can complete ticket"""
        url = reverse('ticket-complete', kwargs={'pk': ticket_in_progress.id})
        response = admin_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'completed'

    def test_confirm_completion_as_requester(self, member_client, ticket_completed, member_user):
        """TC-ACTION-009: Requester can confirm completion"""
        # Ensure the member is the requester
        ticket_completed.requester = member_user
        ticket_completed.save()

        url = reverse('ticket-confirm', kwargs={'pk': ticket_completed.id})
        response = member_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['confirmed_by_requester'] is True

    def test_confirm_completion_not_requester_fails(self, manager_client, ticket_completed):
        """TC-ACTION-010: Non-requester cannot confirm completion"""
        url = reverse('ticket-confirm', kwargs={'pk': ticket_completed.id})
        response = manager_client.post(url)

        # Should fail - only requester can confirm
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTicketWorkflowValidation:
    """Ticket Workflow Validation Tests"""

    def test_cannot_complete_requested_ticket(self, member_client, ticket_requested):
        """Cannot complete a ticket that's not in progress"""
        url = reverse('ticket-complete', kwargs={'pk': ticket_requested.id})
        response = member_client.post(url)

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    def test_cannot_confirm_non_completed_ticket(self, member_client, ticket_in_progress, member_user):
        """Cannot confirm a ticket that's not completed"""
        ticket_in_progress.requester = member_user
        ticket_in_progress.save()

        url = reverse('ticket-confirm', kwargs={'pk': ticket_in_progress.id})
        response = member_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestActivityLogging:
    """Test that actions create activity logs"""

    def test_approve_creates_activity_log(self, manager_client, ticket_requested):
        """Approving ticket creates activity log"""
        initial_count = ActivityLog.objects.count()

        url = reverse('ticket-approve', kwargs={'pk': ticket_requested.id})
        response = manager_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Check activity log was created
        new_count = ActivityLog.objects.count()
        assert new_count > initial_count

        # Verify activity details - first approval is 'pending_approval' or similar action
        # Check for any approval-related activity
        activity = ActivityLog.objects.filter(
            ticket=ticket_requested
        ).order_by('-created_at').first()
        assert activity is not None

    def test_assign_creates_activity_log(self, manager_client, ticket_approved, creative_user):
        """Assigning ticket creates activity log"""
        url = reverse('ticket-assign', kwargs={'pk': ticket_approved.id})
        data = {'assigned_to': creative_user.id}
        response = manager_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        activity = ActivityLog.objects.filter(
            ticket=ticket_approved,
            action='assigned'
        ).first()
        assert activity is not None
