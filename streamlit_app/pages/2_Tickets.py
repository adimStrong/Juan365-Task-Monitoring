"""
Tickets Page - View and manage all tickets
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

# Sidebar with logo
with st.sidebar:
    st.image(str(LOGO_PATH), width=150)
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

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.switch_page("app.py")


def get_tickets(status=None, search=None):
    """Get tickets from API"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_tickets(status=status, search=search)


def get_ticket_comments(ticket_id):
    """Get ticket comments"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_ticket_comments(ticket_id)


def add_comment(ticket_id, comment):
    """Add comment to ticket"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.add_comment(ticket_id, comment)


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
    tickets = get_tickets(status=status, search=search if search else None)

    if not isinstance(tickets, list):
        tickets = tickets.get('results', []) if isinstance(tickets, dict) else []

    st.caption(f"Found {len(tickets)} ticket(s)")

    if tickets:
        for ticket in tickets:
            ticket_id = ticket.get('id')
            title = ticket.get('title')
            status = ticket.get('status')
            priority = ticket.get('priority')
            description = ticket.get('description', '')
            requester = ticket.get('requester', {})
            requester_name = f"{requester.get('first_name', '')} {requester.get('last_name', '')}".strip() or requester.get('username', 'Unknown')
            assigned = ticket.get('assigned_to', {})
            assigned_name = f"{assigned.get('first_name', '')} {assigned.get('last_name', '')}".strip() if assigned else None
            created_at = ticket.get('created_at', '')[:16].replace('T', ' ')
            deadline = ticket.get('deadline', '')[:10] if ticket.get('deadline') else None

            status_emoji = {
                'requested': '🔵', 'approved': '🟢', 'in_progress': '🟡',
                'completed': '✅', 'rejected': '🔴'
            }.get(status, '⚪')

            priority_emoji = {
                'urgent': '🔥', 'high': '🟠', 'medium': '🟡', 'low': '🟢'
            }.get(priority, '')

            with st.expander(f"{status_emoji} {priority_emoji} **#{ticket_id} - {title}**"):
                # Info columns
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown("**Status**")
                    st.write(f"{status_emoji} {status.replace('_', ' ').title() if status else '-'}")
                with col2:
                    st.markdown("**Priority**")
                    st.write(f"{priority_emoji} {priority.title() if priority else '-'}")
                with col3:
                    st.markdown("**Requester**")
                    st.write(f"👤 {requester_name}")
                with col4:
                    st.markdown("**Assigned To**")
                    st.write(f"👤 {assigned_name}" if assigned_name else "⚠️ Unassigned")

                st.markdown("---")

                # Description
                st.markdown("**Description**")
                st.text_area("", value=description, height=80, disabled=True, key=f"desc_{ticket_id}", label_visibility="collapsed")

                # Dates
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"📅 Created: {created_at}")
                with col2:
                    if deadline:
                        st.caption(f"📆 Deadline: {deadline}")

                st.markdown("---")

                # Comments
                st.markdown("**💬 Comments**")
                try:
                    comments = get_ticket_comments(ticket_id)
                    if not isinstance(comments, list):
                        comments = comments.get('results', []) if isinstance(comments, dict) else []

                    if comments:
                        for comment in comments:
                            user_info = comment.get('user', {})
                            user_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() or user_info.get('username', 'User')
                            comment_time = comment.get('created_at', '')[:16].replace('T', ' ')
                            st.markdown(f"**{user_name}** - {comment_time}")
                            st.caption(comment.get('comment', ''))
                    else:
                        st.caption("No comments yet")
                except:
                    st.caption("Could not load comments")

                # Add comment
                with st.form(f"comment_{ticket_id}"):
                    new_comment = st.text_input("Add comment", placeholder="Type your comment...", key=f"input_{ticket_id}")
                    if st.form_submit_button("💬 Send"):
                        if new_comment:
                            try:
                                add_comment(ticket_id, new_comment)
                                st.success("Comment added!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

    else:
        st.info("No tickets found.")
        if st.button("➕ Create First Ticket"):
            st.switch_page("pages/3_Request_Ticket.py")

except Exception as e:
    st.error(f"Error loading tickets: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
