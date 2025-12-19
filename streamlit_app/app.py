"""
Juan365 Ticket Portal
Main Streamlit application with login and dashboard
Supports both local (Django ORM) and online (REST API) modes
"""
import streamlit as st
import os

# Deployment mode - set to 'api' for online, 'local' for local development
def get_config():
    """Get configuration from Streamlit secrets or environment"""
    try:
        api_url = st.secrets.get('API_BASE_URL', os.getenv('API_BASE_URL', 'http://localhost:8000/api'))
        mode = st.secrets.get('DEPLOYMENT_MODE', os.getenv('DEPLOYMENT_MODE', 'api'))
    except:
        api_url = os.getenv('API_BASE_URL', 'http://localhost:8000/api')
        mode = os.getenv('DEPLOYMENT_MODE', 'api')
    return mode, api_url

DEPLOYMENT_MODE, API_BASE_URL = get_config()

# Page configuration
st.set_page_config(
    page_title="Juan365 Ticket Portal",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #3B82F6;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'api_token' not in st.session_state:
    st.session_state.api_token = None


def login_with_api(username: str, password: str):
    """Login using REST API"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL

    result = api.login(username, password)
    if 'access' in result:
        st.session_state.api_token = result['access']
        api.set_token(result['access'])

        # Get user info
        user_info = api.get_me()
        st.session_state.logged_in = True
        st.session_state.user_id = user_info.get('id')
        st.session_state.username = user_info.get('username')
        st.session_state.user_role = user_info.get('role', 'member')
        st.session_state.user_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() or username
        return True
    return False


def login_with_db(username: str, password: str):
    """Login using direct database access"""
    from utils.db import authenticate_user
    user = authenticate_user(username, password)
    if user:
        st.session_state.logged_in = True
        st.session_state.user_id = user.id
        st.session_state.username = user.username
        st.session_state.user_role = user.role
        st.session_state.user_name = f"{user.first_name} {user.last_name}".strip() or user.username
        return True
    return False


def login_page():
    """Display login page"""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Logo
        logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
        with logo_col2:
            st.image("assets/logo.jpg", width=200)
        st.markdown("## Juan365 Ticket Portal")
        st.markdown("---")

        with st.form("login_form"):
            st.markdown("### Login")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")

            col_a, col_b = st.columns(2)
            with col_a:
                submit = st.form_submit_button("🔐 Login", use_container_width=True)
            with col_b:
                if st.form_submit_button("📝 Register", use_container_width=True):
                    st.info("Please register via the main app")

            if submit:
                if username and password:
                    try:
                        if DEPLOYMENT_MODE == 'api':
                            success = login_with_api(username, password)
                        else:
                            success = login_with_db(username, password)

                        if success:
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid credentials or account not approved")
                    except Exception as e:
                        st.error(f"Login error: {str(e)}")
                else:
                    st.warning("Please enter username and password")

        st.markdown("---")
        st.caption(f"Mode: {DEPLOYMENT_MODE.upper()} | API: {API_BASE_URL if DEPLOYMENT_MODE == 'api' else 'Direct DB'}")


def get_stats():
    """Get dashboard statistics"""
    if DEPLOYMENT_MODE == 'api':
        from utils.api_client import get_api_client
        api = get_api_client()
        try:
            return api.get_dashboard_stats()
        except:
            return {'total_tickets': 0, 'pending_approval': 0, 'in_progress': 0, 'completed': 0}
    else:
        from utils.db import get_dashboard_stats
        stats = get_dashboard_stats(st.session_state.user_id)
        return {
            'total_tickets': stats['total'],
            'pending_approval': stats['requested'],
            'in_progress': stats['in_progress'],
            'completed': stats['completed']
        }


def get_recent_tickets():
    """Get recent tickets"""
    if DEPLOYMENT_MODE == 'api':
        from utils.api_client import get_api_client
        api = get_api_client()
        try:
            tickets = api.get_tickets()
            return tickets[:5] if tickets else []
        except:
            return []
    else:
        from utils.db import get_user_tickets
        return list(get_user_tickets(st.session_state.user_id))[:5]


def dashboard_page():
    """Display main dashboard for logged-in users"""
    # Sidebar
    with st.sidebar:
        st.image("assets/logo.jpg", width=120)
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"@{st.session_state.username} • {st.session_state.user_role.title() if st.session_state.user_role else 'User'}")
        st.markdown("---")

        st.markdown("### 📌 Quick Actions")
        if st.button("➕ New Ticket Request", use_container_width=True):
            st.switch_page("pages/1_Request_Ticket.py")
        if st.button("📋 My Tickets", use_container_width=True):
            st.switch_page("pages/2_My_Tickets.py")

        st.markdown("---")

        if st.button("🚪 Logout", use_container_width=True):
            for key in ['logged_in', 'user_id', 'username', 'user_role', 'user_name', 'api_token']:
                st.session_state[key] = None
            st.session_state.logged_in = False
            st.rerun()

        st.markdown("---")
        st.caption(f"Juan365 v2.0 | {DEPLOYMENT_MODE.upper()}")

    # Main content
    st.markdown(f'<p class="main-header">Welcome, {st.session_state.user_name}! 👋</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Manage your tickets and requests</p>', unsafe_allow_html=True)

    try:
        # Get stats
        stats = get_stats()

        # Dashboard stats
        st.markdown("### 📊 Ticket Summary")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(label="📋 Total", value=stats.get('total_tickets', stats.get('total', 0)))
        with col2:
            st.metric(label="🔵 Pending", value=stats.get('pending_approval', stats.get('requested', 0)))
        with col3:
            st.metric(label="🟡 In Progress", value=stats.get('in_progress', 0))
        with col4:
            st.metric(label="✅ Completed", value=stats.get('completed', 0))

        st.markdown("---")

        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("➕ Request New Ticket", use_container_width=True, type="primary"):
                st.switch_page("pages/1_Request_Ticket.py")
        with col2:
            if st.button("📋 View My Tickets", use_container_width=True):
                st.switch_page("pages/2_My_Tickets.py")

        st.markdown("---")

        # Recent tickets
        st.markdown("### 🕐 Recent Tickets")
        recent_tickets = get_recent_tickets()

        if recent_tickets:
            for ticket in recent_tickets:
                # Handle both dict (API) and object (ORM) formats
                if isinstance(ticket, dict):
                    ticket_id = ticket.get('id')
                    title = ticket.get('title')
                    status = ticket.get('status')
                    created_at = ticket.get('created_at', '')[:10]
                else:
                    ticket_id = ticket.id
                    title = ticket.title
                    status = ticket.status
                    created_at = ticket.created_at.strftime('%m/%d/%Y')

                status_emoji = {
                    'requested': '🔵',
                    'approved': '🟢',
                    'in_progress': '🟡',
                    'completed': '✅',
                    'rejected': '🔴'
                }.get(status, '⚪')

                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                with col1:
                    st.write(f"{status_emoji} **#{ticket_id}** - {title}")
                with col2:
                    st.caption(status.replace('_', ' ').title() if status else '-')
                with col3:
                    st.caption(created_at)
                with col4:
                    if st.button("View", key=f"view_{ticket_id}"):
                        st.session_state.selected_ticket_id = ticket_id
                        st.switch_page("pages/2_My_Tickets.py")
        else:
            st.info("No tickets yet. Click 'Request New Ticket' to create one!")

    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")


# Main app logic
if st.session_state.logged_in:
    dashboard_page()
else:
    login_page()
