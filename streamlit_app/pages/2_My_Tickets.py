"""
My Tickets Page
View and manage your tickets - supports both local and API modes
"""
import streamlit as st
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get configuration
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

st.set_page_config(
    page_title="My Tickets - Juan365",
    page_icon="📋",
    layout="wide"
)

# Check if user is logged in
if not st.session_state.get('logged_in', False):
    st.warning("Please login first")
    if st.button("Go to Login"):
        st.switch_page("app.py")
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user_name}")
    st.caption(f"@{st.session_state.username}")
    st.markdown("---")

    if st.button("🏠 Dashboard", use_container_width=True):
        st.switch_page("app.py")
    if st.button("➕ New Request", use_container_width=True):
        st.switch_page("pages/1_Request_Ticket.py")

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.switch_page("app.py")

# Main content
st.title("📋 My Tickets")

# Filters
col1, col2 = st.columns([2, 1])

with col1:
    search = st.text_input("🔍 Search", placeholder="Search tickets...")
with col2:
    status_filter = st.selectbox(
        "Status",
        options=["all", "requested", "approved", "in_progress", "completed", "rejected"],
        format_func=lambda x: x.replace("_", " ").title() if x != "all" else "All Status"
    )

st.markdown("---")


def get_tickets_api(status=None, search=None):
    """Get tickets via REST API"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_tickets(status=status, search=search)


def get_ticket_detail_api(ticket_id):
    """Get single ticket detail via API"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_ticket(ticket_id)


def get_ticket_comments_api(ticket_id):
    """Get ticket comments via API"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_ticket_comments(ticket_id)


def add_comment_api(ticket_id, comment):
    """Add comment via API"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.add_comment(ticket_id, comment)


try:
    if DEPLOYMENT_MODE == 'api':
        # API mode
        status = status_filter if status_filter != 'all' else None
        tickets = get_tickets_api(status=status, search=search if search else None)

        if not isinstance(tickets, list):
            tickets = tickets.get('results', []) if isinstance(tickets, dict) else []

    else:
        # Local database mode
        from utils.db import get_user_tickets, get_ticket_comments, add_ticket_comment, get_ticket_attachments
        from django.db.models import Q

        tickets = get_user_tickets(st.session_state.user_id)

        # Apply filters
        if status_filter != "all":
            tickets = tickets.filter(status=status_filter)

        if search:
            tickets = tickets.filter(Q(title__icontains=search) | Q(description__icontains=search))

        tickets = list(tickets.order_by('-created_at'))

    st.caption(f"Found {len(tickets)} ticket(s)")

    if tickets:
        for ticket in tickets:
            # Handle both dict (API) and object (ORM) formats
            if isinstance(ticket, dict):
                ticket_id = ticket.get('id')
                title = ticket.get('title')
                status = ticket.get('status')
                priority = ticket.get('priority')
                description = ticket.get('description', '')
                requester = ticket.get('requester', {})
                requester_name = f"{requester.get('first_name', '')} {requester.get('last_name', '')}".strip() if requester else 'Unknown'
                assigned = ticket.get('assigned_to', {})
                assigned_name = f"{assigned.get('first_name', '')} {assigned.get('last_name', '')}".strip() if assigned else None
                created_at = ticket.get('created_at', '')[:16].replace('T', ' ')
                updated_at = ticket.get('updated_at', '')[:16].replace('T', ' ')
                deadline = ticket.get('deadline', '')[:10] if ticket.get('deadline') else None
            else:
                ticket_id = ticket.id
                title = ticket.title
                status = ticket.status
                priority = ticket.priority
                description = ticket.description
                requester_name = f"{ticket.requester.first_name} {ticket.requester.last_name}" if ticket.requester else 'Unknown'
                assigned_name = f"{ticket.assigned_to.first_name} {ticket.assigned_to.last_name}" if ticket.assigned_to else None
                created_at = ticket.created_at.strftime('%Y-%m-%d %H:%M')
                updated_at = ticket.updated_at.strftime('%Y-%m-%d %H:%M')
                deadline = ticket.deadline.strftime('%Y-%m-%d') if ticket.deadline else None

            status_emoji = {
                'requested': '🔵',
                'approved': '🟢',
                'in_progress': '🟡',
                'completed': '✅',
                'rejected': '🔴'
            }.get(status, '⚪')

            priority_emoji = {
                'urgent': '🔥',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(priority, '')

            with st.expander(f"{status_emoji} {priority_emoji} **#{ticket_id} - {title}**", expanded=False):
                # Header info
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
                    if assigned_name:
                        st.write(f"👤 {assigned_name}")
                    else:
                        st.write("⚠️ Unassigned")

                st.markdown("---")

                # Description
                st.markdown("**Description**")
                st.text_area(
                    "desc",
                    value=description,
                    height=100,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"desc_{ticket_id}"
                )

                # Dates
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption(f"📅 Created: {created_at}")
                with col2:
                    st.caption(f"🔄 Updated: {updated_at}")
                with col3:
                    if deadline:
                        st.caption(f"📆 Deadline: {deadline}")

                st.markdown("---")

                # Comments section
                st.markdown("**💬 Comments**")

                if DEPLOYMENT_MODE == 'api':
                    try:
                        comments = get_ticket_comments_api(ticket_id)
                        if not isinstance(comments, list):
                            comments = comments.get('results', []) if isinstance(comments, dict) else []
                    except:
                        comments = []
                else:
                    comments = list(get_ticket_comments(ticket_id))

                if comments:
                    for comment in comments:
                        if isinstance(comment, dict):
                            user_info = comment.get('user', {})
                            user_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() or user_info.get('username', 'User')
                            comment_time = comment.get('created_at', '')[:16].replace('T', ' ')
                            comment_text = comment.get('comment', '')
                        else:
                            user_name = comment.user.first_name
                            comment_time = comment.created_at.strftime('%m/%d %H:%M')
                            comment_text = comment.comment

                        st.markdown(f"**{user_name}** - {comment_time}")
                        st.caption(comment_text)
                else:
                    st.caption("No comments yet")

                # Add comment form
                with st.form(f"comment_form_{ticket_id}"):
                    new_comment = st.text_input("Add a comment", placeholder="Type your comment...", key=f"comment_input_{ticket_id}")
                    if st.form_submit_button("💬 Send", key=f"send_comment_{ticket_id}"):
                        if new_comment:
                            try:
                                if DEPLOYMENT_MODE == 'api':
                                    add_comment_api(ticket_id, new_comment)
                                else:
                                    add_ticket_comment(ticket_id, st.session_state.user_id, new_comment)
                                st.success("Comment added!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

    else:
        st.info("No tickets found. Create a new request to get started!")
        if st.button("➕ Create New Request"):
            st.switch_page("pages/1_Request_Ticket.py")

except Exception as e:
    st.error(f"Error loading tickets: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
