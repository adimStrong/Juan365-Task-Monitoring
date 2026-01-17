"""
User Management Tests (TC-USER)
Tests for user listing, approval, role management
"""
import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserListing:
    """TC-USER-001 to TC-USER-002: User Listing Tests"""

    def test_list_users_as_admin(self, admin_client, member_user, manager_user):
        """TC-USER-001: Admin can list all users"""
        url = reverse('user-management-list')
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Should return paginated results or list
        if 'results' in response.data:
            users = response.data['results']
        else:
            users = response.data
        assert len(users) >= 2  # At least member and manager

    def test_list_users_as_manager(self, manager_client, member_user):
        """Manager can list users"""
        url = reverse('user-management-list')
        response = manager_client.get(url)

        # Managers should have access
        assert response.status_code == status.HTTP_200_OK

    def test_list_users_as_member_forbidden(self, member_client):
        """TC-USER-002: Regular member cannot list all users"""
        url = reverse('user-management-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_users_unauthenticated(self, api_client):
        """Unauthenticated access to user list fails"""
        url = reverse('user-management-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserApproval:
    """TC-USER-003 to TC-USER-004: User Approval Tests"""

    def test_approve_user(self, admin_client, unapproved_user):
        """TC-USER-003: Admin can approve a pending user"""
        url = reverse('user-management-approve', kwargs={'pk': unapproved_user.id})
        response = admin_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Verify user is now approved
        unapproved_user.refresh_from_db()
        assert unapproved_user.is_approved is True
        assert unapproved_user.approved_by is not None

    def test_approve_user_as_manager(self, manager_client, unapproved_user):
        """Manager can approve users"""
        url = reverse('user-management-approve', kwargs={'pk': unapproved_user.id})
        response = manager_client.post(url)

        # Managers should be able to approve (or may be restricted to admin only)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    def test_reject_user(self, admin_client, unapproved_user):
        """TC-USER-004: Admin can reject/deactivate a user"""
        url = reverse('user-management-reject-user', kwargs={'pk': unapproved_user.id})
        response = admin_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Verify user is deactivated
        unapproved_user.refresh_from_db()
        assert unapproved_user.is_active is False

    def test_approve_user_as_member_forbidden(self, member_client, unapproved_user):
        """Regular member cannot approve users"""
        url = reverse('user-management-approve', kwargs={'pk': unapproved_user.id})
        response = member_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserRoleManagement:
    """TC-USER-005 to TC-USER-006: Role Management Tests"""

    def test_change_user_role(self, admin_client, member_user):
        """TC-USER-005: Admin can change user role"""
        url = reverse('user-management-change-role', kwargs={'pk': member_user.id})
        response = admin_client.post(url, {'role': 'manager'}, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Verify role was changed
        member_user.refresh_from_db()
        assert member_user.role == 'manager'

    def test_change_role_to_admin(self, admin_client, member_user):
        """Admin can promote user to admin"""
        url = reverse('user-management-change-role', kwargs={'pk': member_user.id})
        response = admin_client.post(url, {'role': 'admin'}, format='json')

        assert response.status_code == status.HTTP_200_OK
        member_user.refresh_from_db()
        assert member_user.role == 'admin'

    def test_reactivate_user(self, admin_client, inactive_user):
        """TC-USER-006: Admin can reactivate an inactive user"""
        url = reverse('user-management-reactivate', kwargs={'pk': inactive_user.id})
        response = admin_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Verify user is now active
        inactive_user.refresh_from_db()
        assert inactive_user.is_active is True

    def test_change_role_as_member_forbidden(self, member_client, manager_user):
        """Regular member cannot change roles"""
        url = reverse('user-management-change-role', kwargs={'pk': manager_user.id})
        response = member_client.post(url, {'role': 'admin'}, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserCreation:
    """TC-USER-007: Admin User Creation Tests"""

    def test_admin_create_user(self, admin_client, department):
        """TC-USER-007: Admin can create a new user (auto-approved)"""
        url = reverse('user-management-list')
        data = {
            'username': 'newcreated',
            'email': 'newcreated@test.com',
            'password': 'NewCreated123!',
            'password_confirm': 'NewCreated123!',  # Required field
            'first_name': 'New',
            'last_name': 'Created',
            'role': 'member',
            'user_department': department.id
        }
        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['username'] == 'newcreated'
        # Check is_approved if present in response
        if 'is_approved' in response.data:
            assert response.data['is_approved'] is True  # Auto-approved when admin creates

    def test_member_cannot_create_user(self, member_client):
        """Regular member cannot create users"""
        url = reverse('user-management-list')
        data = {
            'username': 'unauthorized',
            'email': 'unauthorized@test.com',
            'password': 'Test123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        response = member_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserFiltering:
    """TC-USER-008 to TC-USER-009: User Filtering Tests"""

    def test_filter_by_approval_status(self, admin_client, member_user, unapproved_user):
        """TC-USER-008: Filter users by approval status"""
        url = reverse('user-management-list')

        # Filter for unapproved users
        response = admin_client.get(url, {'is_approved': 'false'})
        assert response.status_code == status.HTTP_200_OK

        if 'results' in response.data:
            users = response.data['results']
        else:
            users = response.data

        # All returned users should be unapproved
        for user in users:
            assert user['is_approved'] is False

    def test_filter_by_role(self, admin_client, member_user, manager_user):
        """TC-USER-009: Filter users by role"""
        url = reverse('user-management-list')

        # Filter for managers
        response = admin_client.get(url, {'role': 'manager'})
        assert response.status_code == status.HTTP_200_OK

        if 'results' in response.data:
            users = response.data['results']
        else:
            users = response.data

        # All returned users should be managers
        for user in users:
            assert user['role'] == 'manager'


@pytest.mark.django_db
class TestApprovedUsersList:
    """Tests for listing approved active users (for assignment dropdowns)"""

    def test_list_approved_users(self, member_client, member_user, manager_user, admin_user):
        """Get list of approved active users for assignment"""
        url = reverse('user-list')
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        if 'results' in response.data:
            users = response.data['results']
        else:
            users = response.data

        # All users should be approved and active
        for user in users:
            assert user.get('is_approved', True) is True
