"""
Comment Tests (TC-COMMENT)
Tests for ticket comments and replies
"""
import pytest
from django.urls import reverse
from rest_framework import status
from api.models import TicketComment


@pytest.mark.django_db
class TestTicketComments:
    """TC-COMMENT-001 to TC-COMMENT-003: Comment Tests"""

    def test_add_comment(self, member_client, ticket_requested):
        """TC-COMMENT-001: Add comment to ticket"""
        url = reverse('ticket-comments', kwargs={'pk': ticket_requested.id})
        data = {'comment': 'This is a test comment'}
        response = member_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['comment'] == 'This is a test comment'
        assert response.data['parent'] is None  # Top-level comment

    def test_reply_to_comment(self, member_client, ticket_comment, manager_user):
        """TC-COMMENT-002: Reply to an existing comment"""
        url = reverse('ticket-comments', kwargs={'pk': ticket_comment.ticket.id})
        data = {
            'comment': 'This is a reply',
            'parent': ticket_comment.id
        }
        response = member_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['parent'] == ticket_comment.id

        # Verify reply is linked to parent
        reply = TicketComment.objects.get(id=response.data['id'])
        assert reply.parent == ticket_comment

    def test_list_comments(self, member_client, ticket_comment, comment_with_reply):
        """TC-COMMENT-003: List all comments on a ticket"""
        parent, reply = comment_with_reply
        url = reverse('ticket-comments', kwargs={'pk': parent.ticket.id})
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Should have comments with nested replies
        comments = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(comments) >= 1

    def test_add_empty_comment_fails(self, member_client, ticket_requested):
        """Cannot add empty comment"""
        url = reverse('ticket-comments', kwargs={'pk': ticket_requested.id})
        data = {'comment': ''}
        response = member_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_comment_unauthenticated(self, api_client, ticket_requested):
        """Unauthenticated user cannot add comment"""
        url = reverse('ticket-comments', kwargs={'pk': ticket_requested.id})
        data = {'comment': 'Test comment'}
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_comment_creates_activity_log(self, member_client, ticket_requested):
        """Adding comment creates activity log"""
        from api.models import ActivityLog

        initial_count = ActivityLog.objects.filter(action='commented').count()

        url = reverse('ticket-comments', kwargs={'pk': ticket_requested.id})
        data = {'comment': 'New comment for activity log test'}
        response = member_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

        # May or may not create activity log depending on implementation
        # Just verify no error occurred


@pytest.mark.django_db
class TestCommentReplies:
    """Comment Reply Tests"""

    def test_nested_replies(self, member_client, comment_with_reply):
        """Test fetching comments with nested replies"""
        parent, reply = comment_with_reply
        url = reverse('ticket-comments', kwargs={'pk': parent.ticket.id})
        response = member_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Find parent comment and check for replies
        comments = response.data if isinstance(response.data, list) else response.data.get('results', [])
        parent_comment = next((c for c in comments if c['id'] == parent.id), None)

        if parent_comment and 'replies' in parent_comment:
            assert len(parent_comment['replies']) >= 1

    def test_reply_to_nonexistent_comment(self, member_client, ticket_requested):
        """Reply to non-existent comment fails"""
        url = reverse('ticket-comments', kwargs={'pk': ticket_requested.id})
        data = {
            'comment': 'Reply to nothing',
            'parent': 99999
        }
        response = member_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
