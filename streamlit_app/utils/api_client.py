"""
API Client for Streamlit
Connects to Django REST API for online deployment
"""
import requests
import streamlit as st
from typing import Optional, Dict, Any, List
import os

# API Configuration - can be overridden by environment variable or Streamlit secrets
def get_api_base_url():
    # Try Streamlit secrets first (for Streamlit Cloud)
    try:
        return st.secrets.get('API_BASE_URL', os.getenv('API_BASE_URL', 'http://localhost:8000/api'))
    except:
        return os.getenv('API_BASE_URL', 'http://localhost:8000/api')

API_BASE_URL = get_api_base_url()


class APIClient:
    """REST API client for the ticketing system"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or API_BASE_URL
        self.token = None

    def set_token(self, token: str):
        """Set the authentication token"""
        self.token = token

    def _headers(self) -> Dict[str, str]:
        """Get request headers with auth token"""
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def _request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make an API request"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=self._headers(),
                timeout=30
            )
            if not response.ok:
                # Try to get detailed error message from response
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        # Format validation errors nicely
                        errors = []
                        for field, messages in error_data.items():
                            if isinstance(messages, list):
                                errors.append(f"{field}: {', '.join(messages)}")
                            else:
                                errors.append(f"{field}: {messages}")
                        raise Exception("; ".join(errors) if errors else str(error_data))
                except ValueError:
                    pass
                response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            raise Exception(f"API Error: {str(e)}")

    # =====================
    # AUTHENTICATION
    # =====================

    def login(self, username: str, password: str) -> Dict:
        """Login and get tokens"""
        response = self._request('POST', '/auth/login/', {'username': username, 'password': password})
        if 'access' in response:
            self.token = response['access']
        return response

    def get_me(self) -> Dict:
        """Get current user info"""
        return self._request('GET', '/auth/me/')

    # =====================
    # TICKETS
    # =====================

    def get_tickets(self, status: str = None, search: str = None) -> List[Dict]:
        """Get list of tickets"""
        params = {}
        if status and status != 'all':
            params['status'] = status
        if search:
            params['search'] = search
        response = self._request('GET', '/tickets/', params=params)
        return response.get('results', response) if isinstance(response, dict) else response

    def get_ticket(self, ticket_id: int) -> Dict:
        """Get single ticket details"""
        return self._request('GET', f'/tickets/{ticket_id}/')

    def create_ticket(self, title: str, description: str, priority: str,
                      deadline: str = None, assigned_to: int = None) -> Dict:
        """Create a new ticket"""
        data = {
            'title': title,
            'description': description,
            'priority': priority,
        }
        if deadline:
            data['deadline'] = deadline
        if assigned_to:
            data['assigned_to'] = assigned_to
        return self._request('POST', '/tickets/', data)

    def get_ticket_comments(self, ticket_id: int) -> List[Dict]:
        """Get comments for a ticket"""
        return self._request('GET', f'/tickets/{ticket_id}/comments/')

    def add_comment(self, ticket_id: int, comment: str, parent_id: int = None) -> Dict:
        """Add a comment to a ticket"""
        data = {'comment': comment}
        if parent_id:
            data['parent'] = parent_id
        return self._request('POST', f'/tickets/{ticket_id}/comments/', data)

    def upload_attachment(self, ticket_id: int, file_data: bytes, file_name: str) -> Dict:
        """Upload attachment to a ticket"""
        url = f"{self.base_url}/tickets/{ticket_id}/attachments/"
        files = {'file': (file_name, file_data)}
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        response = requests.post(url, files=files, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()

    # =====================
    # TICKET ACTIONS
    # =====================

    def approve_ticket(self, ticket_id: int) -> Dict:
        """Approve a ticket (manager only)"""
        return self._request('POST', f'/tickets/{ticket_id}/approve/')

    def reject_ticket(self, ticket_id: int, reason: str = '') -> Dict:
        """Reject a ticket (manager only)"""
        data = {'reason': reason} if reason else {}
        return self._request('POST', f'/tickets/{ticket_id}/reject/', data)

    def assign_ticket(self, ticket_id: int, user_id: int) -> Dict:
        """Assign ticket to a user (manager only)"""
        return self._request('POST', f'/tickets/{ticket_id}/assign/', {'assigned_to': user_id})

    def start_ticket(self, ticket_id: int) -> Dict:
        """Start working on a ticket"""
        return self._request('POST', f'/tickets/{ticket_id}/start/')

    def complete_ticket(self, ticket_id: int) -> Dict:
        """Mark ticket as completed"""
        return self._request('POST', f'/tickets/{ticket_id}/complete/')

    # =====================
    # USERS
    # =====================

    def get_users(self) -> List[Dict]:
        """Get list of users"""
        response = self._request('GET', '/users/')
        return response if isinstance(response, list) else response.get('results', [])

    def get_all_users_manage(self) -> List[Dict]:
        """Get all users for management (admin only)"""
        response = self._request('GET', '/users/manage/')
        return response if isinstance(response, list) else response.get('results', [])

    def create_user(self, username: str, email: str, password: str,
                    first_name: str = '', last_name: str = '', role: str = 'member') -> Dict:
        """Create a new user (admin only)"""
        data = {
            'username': username,
            'email': email,
            'password': password,
            'password_confirm': password,  # API requires this field
            'first_name': first_name,
            'last_name': last_name,
            'role': role
        }
        return self._request('POST', '/users/manage/', data)

    def approve_user(self, user_id: int) -> Dict:
        """Approve a user (admin only)"""
        return self._request('POST', f'/users/manage/{user_id}/approve/')

    def reset_user_password(self, user_id: int, new_password: str) -> Dict:
        """Reset user password (admin only)"""
        return self._request('POST', f'/users/manage/{user_id}/reset-password/', {'password': new_password})

    def change_user_role(self, user_id: int, role: str) -> Dict:
        """Change user role (admin only)"""
        return self._request('POST', f'/users/manage/{user_id}/change_role/', {'role': role})

    # =====================
    # DASHBOARD
    # =====================

    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        return self._request('GET', '/dashboard/stats/')

    def get_my_tasks(self) -> List[Dict]:
        """Get current user's tasks"""
        return self._request('GET', '/dashboard/my-tasks/')


# Global API client instance
api_client = APIClient()


def get_api_client() -> APIClient:
    """Get the API client, initializing from session state if needed"""
    if 'api_token' in st.session_state and st.session_state.api_token:
        api_client.set_token(st.session_state.api_token)
    return api_client
