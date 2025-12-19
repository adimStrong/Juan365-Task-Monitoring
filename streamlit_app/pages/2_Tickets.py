"""
Tickets Page - View all tickets in a clean list
"""
import streamlit as st
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    page_title="Tickets - Juan365",
    page_icon="📋",
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
    if st.button("📋 Tickets", use_container_width=True, type="primary"):
        st.switch_page("pages/2_Tickets.py")
    if st.button("➕ New Request", use_container_width=True):
        st.switch_page("pages/3_Request_Ticket.py")
    if st.button("👥 Activity & Users", use_container_width=True):
        st.switch_page("pages/4_Activity_Users.py")
    if st.button("📝 My Tasks", use_container_width=True):
        st.switch_page("pages/5_My_Tasks.py")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.switch_page("app.py")


@st.cache_data(ttl=30)
def get_tickets(_token, status=None, search=None):
    """Get tickets from API (cached)"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_tickets(status=status, search=search)


def view_ticket(ticket_id):
    """Navigate to ticket detail page"""
    st.session_state.view_ticket_id = ticket_id
    st.switch_page("pages/Ticket_Detail.py")


# Main content
st.title("📋 All Tickets")

# Filters
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    search = st.text_input("🔍 Search", placeholder="Search tickets by title...")
with col2:
    status_filter = st.selectbox(
        "Status",
        options=["all", "requested", "approved", "in_progress", "completed", "rejected"],
        format_func=lambda x: x.replace("_", " ").title() if x != "all" else "All Status"
    )
with col3:
    if st.button("➕ New Ticket", type="primary", use_container_width=True):
        st.switch_page("pages/3_Request_Ticket.py")

st.markdown("---")

try:
    status = status_filter if status_filter != 'all' else None
    token = st.session_state.get('api_token', '')
    tickets = get_tickets(token, status=status, search=search if search else None)

    if not isinstance(tickets, list):
        tickets = tickets.get('results', []) if isinstance(tickets, dict) else []

    st.caption(f"Found {len(tickets)} ticket(s) • Click on a ticket to view details")

    if tickets:
        # Table header
        header_cols = st.columns([0.5, 2.5, 1, 1, 1.5, 1])
        with header_cols[0]:
            st.markdown("**#**")
        with header_cols[1]:
            st.markdown("**Title**")
        with header_cols[2]:
            st.markdown("**Status**")
        with header_cols[3]:
            st.markdown("**Priority**")
        with header_cols[4]:
            st.markdown("**Assigned**")
        with header_cols[5]:
            st.markdown("**Action**")

        st.markdown("---")

        for ticket in tickets:
            ticket_id = ticket.get('id')
            title = ticket.get('title', 'Untitled')
            status = ticket.get('status', 'unknown')
            priority = ticket.get('priority', 'medium')
            assigned = ticket.get('assigned_to', {})
            assigned_name = f"{assigned.get('first_name', '')} {assigned.get('last_name', '')}".strip() if assigned else "—"
            deadline = ticket.get('deadline', '')[:10] if ticket.get('deadline') else None

            status_emoji = {
                'requested': '🔵', 'approved': '🟢', 'in_progress': '🟡',
                'completed': '✅', 'rejected': '🔴'
            }.get(status, '⚪')

            priority_emoji = {
                'urgent': '🔥', 'high': '🟠', 'medium': '🟡', 'low': '🟢'
            }.get(priority, '')

            # Ticket row
            row_cols = st.columns([0.5, 2.5, 1, 1, 1.5, 1])

            with row_cols[0]:
                st.write(f"**{ticket_id}**")
            with row_cols[1]:
                # Truncate title if too long
                display_title = title[:40] + "..." if len(title) > 40 else title
                st.write(display_title)
            with row_cols[2]:
                st.write(f"{status_emoji} {status.replace('_', ' ').title()}")
            with row_cols[3]:
                st.write(f"{priority_emoji} {priority.title()}")
            with row_cols[4]:
                st.write(assigned_name if assigned_name != "—" else "⚠️ Unassigned")
            with row_cols[5]:
                if st.button("View", key=f"view_{ticket_id}", use_container_width=True):
                    view_ticket(ticket_id)

            # Add subtle divider
            st.markdown("<hr style='margin: 5px 0; opacity: 0.2;'>", unsafe_allow_html=True)

    else:
        st.info("No tickets found.")
        if st.button("➕ Create First Ticket"):
            st.switch_page("pages/3_Request_Ticket.py")

except Exception as e:
    st.error(f"Error loading tickets: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
