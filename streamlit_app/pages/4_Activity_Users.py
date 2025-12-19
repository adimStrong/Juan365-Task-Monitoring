"""
Activity & Users Page - View activity logs and manage users
"""
import streamlit as st
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get logo path
LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo.jpg"

# Get configuration
def get_config():
    try:
        api_url = st.secrets.get('API_BASE_URL', os.getenv('API_BASE_URL', 'http://localhost:8000/api'))
        mode = st.secrets.get('DEPLOYMENT_MODE', os.getenv('DEPLOYMENT_MODE', 'api'))
    except:
        api_url = os.getenv('API_BASE_URL', 'http://localhost:8000/api')
        mode = os.getenv('DEPLOYMENT_MODE', 'api')
    return mode, api_url

DEPLOYMENT_MODE, API_BASE_URL = get_config()

st.set_page_config(
    page_title="Activity & Users - Juan365",
    page_icon="👥",
    layout="wide"
)

# Check login
if not st.session_state.get('logged_in', False):
    st.warning("Please login first")
    if st.button("Go to Login"):
        st.switch_page("app.py")
    st.stop()

# Sidebar navigation
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.get('user_name', 'User')}")
    st.caption(f"@{st.session_state.get('username', '')} • {(st.session_state.get('user_role') or 'User').title()}")
    st.markdown("---")

    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/1_Dashboard.py")
    if st.button("📋 Tickets", use_container_width=True):
        st.switch_page("pages/2_Tickets.py")
    if st.button("➕ New Request", use_container_width=True):
        st.switch_page("pages/3_Request_Ticket.py")
    if st.button("👥 Activity & Users", use_container_width=True, type="primary"):
        st.switch_page("pages/4_Activity_Users.py")
    if st.button("📝 My Tasks", use_container_width=True):
        st.switch_page("pages/5_My_Tasks.py")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.switch_page("app.py")


def get_users():
    """Get all users from API"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_users()


def get_all_users_manage():
    """Get all users for management (admin only)"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_all_users_manage()


def create_user(username, email, password, first_name, last_name, role):
    """Create a new user (admin only)"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.create_user(username, email, password, first_name, last_name, role)


def approve_user(user_id):
    """Approve a user (admin only)"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.approve_user(user_id)


def get_activity_logs():
    """Get activity logs from API"""
    import requests
    headers = {'Content-Type': 'application/json'}
    if st.session_state.get('api_token'):
        headers['Authorization'] = f'Bearer {st.session_state.api_token}'
    try:
        response = requests.get(f"{API_BASE_URL}/activity/", headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except:
        return []


# Main content
st.title("👥 Activity & Users")

# Check if user is admin/manager
is_admin = st.session_state.get('user_role') in ['admin', 'manager']

# Tabs - show manage tab only for admins
if is_admin:
    tab1, tab2, tab3 = st.tabs(["📋 Activity Log", "👥 Users", "➕ Manage Users"])
else:
    tab1, tab2 = st.tabs(["📋 Activity Log", "👥 Users"])

with tab1:
    st.markdown("### Recent Activity")
    st.markdown("---")

    try:
        activities = get_activity_logs()

        if not isinstance(activities, list):
            activities = activities.get('results', []) if isinstance(activities, dict) else []

        if activities:
            for activity in activities[:20]:
                action = activity.get('action', 'Unknown action')
                user_info = activity.get('user', {})
                user_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() or user_info.get('username', 'System')
                timestamp = activity.get('created_at', '')[:16].replace('T', ' ')
                ticket_info = activity.get('ticket', {})
                ticket_id = ticket_info.get('id') if ticket_info else None

                # Action icons
                action_icons = {
                    'created': '➕',
                    'approved': '✅',
                    'rejected': '❌',
                    'assigned': '👤',
                    'started': '🚀',
                    'completed': '🎉',
                    'commented': '💬',
                }
                icon = action_icons.get(action.lower().split()[0] if action else '', '📝')

                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.write(f"{icon}")
                with col2:
                    ticket_ref = f" on **#{ticket_id}**" if ticket_id else ""
                    st.write(f"**{user_name}** {action}{ticket_ref}")
                with col3:
                    st.caption(timestamp)

                st.markdown("---")
        else:
            st.info("No activity logs available yet.")

    except Exception as e:
        st.warning(f"Could not load activity logs: {str(e)}")
        st.info("Activity logging may not be enabled on this server.")

with tab2:
    st.markdown("### Team Members")
    st.markdown("---")

    try:
        users = get_users()

        if not isinstance(users, list):
            users = users.get('results', []) if isinstance(users, dict) else []

        if users:
            # Summary
            col1, col2, col3 = st.columns(3)
            admins = len([u for u in users if u.get('role') == 'admin'])
            managers = len([u for u in users if u.get('role') == 'manager'])
            members = len([u for u in users if u.get('role') == 'member'])

            with col1:
                st.metric("👑 Admins", admins)
            with col2:
                st.metric("👔 Managers", managers)
            with col3:
                st.metric("👤 Members", members)

            st.markdown("---")

            # User list
            for user in users:
                user_id = user.get('id')
                username = user.get('username', 'unknown')
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                full_name = f"{first_name} {last_name}".strip() or username
                email = user.get('email', 'No email')
                role = user.get('role', 'member')
                is_active = user.get('is_active', True)
                is_approved = user.get('is_approved', True)

                role_emoji = {
                    'admin': '👑',
                    'manager': '👔',
                    'member': '👤'
                }.get(role, '👤')

                status_color = "🟢" if is_active and is_approved else "🔴"

                with st.expander(f"{role_emoji} {full_name} (@{username})"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("**Role**")
                        st.write(f"{role_emoji} {role.title()}")

                    with col2:
                        st.markdown("**Email**")
                        st.write(email)

                    with col3:
                        st.markdown("**Status**")
                        if is_active and is_approved:
                            st.write(f"{status_color} Active")
                        elif not is_approved:
                            st.write(f"{status_color} Pending Approval")
                        else:
                            st.write(f"{status_color} Inactive")

        else:
            st.info("No users found.")

    except Exception as e:
        st.error(f"Error loading users: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# Admin-only: Manage Users tab
if is_admin:
    with tab3:
        st.markdown("### User Management")
        st.info("Create new users or approve pending registrations")
        st.markdown("---")

        # Create User Form
        st.markdown("#### ➕ Create New User")
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_username = st.text_input("Username *", placeholder="e.g. jdoe")
                new_email = st.text_input("Email *", placeholder="e.g. john@company.com")
                new_password = st.text_input("Password *", type="password", placeholder="Min 8 characters")

            with col2:
                new_first_name = st.text_input("First Name", placeholder="John")
                new_last_name = st.text_input("Last Name", placeholder="Doe")
                new_role = st.selectbox(
                    "Role",
                    options=["member", "manager", "admin"],
                    format_func=lambda x: {
                        'member': '👤 Member',
                        'manager': '👔 Manager',
                        'admin': '👑 Admin'
                    }.get(x, x)
                )

            if st.form_submit_button("👤 Create User", type="primary"):
                if not new_username:
                    st.error("Username is required")
                elif not new_email:
                    st.error("Email is required")
                elif not new_password or len(new_password) < 8:
                    st.error("Password must be at least 8 characters")
                else:
                    try:
                        result = create_user(
                            username=new_username,
                            email=new_email,
                            password=new_password,
                            first_name=new_first_name,
                            last_name=new_last_name,
                            role=new_role
                        )
                        st.success(f"User '{new_username}' created successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating user: {str(e)}")

        st.markdown("---")

        # Pending Users Section
        st.markdown("#### ⏳ Pending Approvals")
        try:
            all_users = get_all_users_manage()
            if not isinstance(all_users, list):
                all_users = all_users.get('results', []) if isinstance(all_users, dict) else []

            pending_users = [u for u in all_users if not u.get('is_approved', True)]

            if pending_users:
                for user in pending_users:
                    user_id = user.get('id')
                    username = user.get('username', 'unknown')
                    email = user.get('email', '')
                    first_name = user.get('first_name', '')
                    last_name = user.get('last_name', '')
                    full_name = f"{first_name} {last_name}".strip() or username

                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"🔴 **{full_name}** (@{username})")
                    with col2:
                        st.caption(email)
                    with col3:
                        if st.button("✅ Approve", key=f"approve_{user_id}"):
                            try:
                                approve_user(user_id)
                                st.success(f"User '{username}' approved!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
            else:
                st.success("No pending approvals. All users are approved!")

        except Exception as e:
            st.warning(f"Could not load pending users: {str(e)}")
