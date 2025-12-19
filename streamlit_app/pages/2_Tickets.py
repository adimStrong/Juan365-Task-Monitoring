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


@st.cache_data(ttl=30)  # Cache for 30 seconds
def get_tickets(_token, status=None, search=None):
    """Get tickets from API (cached)"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_tickets(status=status, search=search)


@st.cache_data(ttl=60)  # Cache comments for 60 seconds
def get_ticket_comments(_token, ticket_id):
    """Get ticket comments (cached)"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_ticket_comments(ticket_id)


def add_comment(ticket_id, comment):
    """Add comment to ticket"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    result = api.add_comment(ticket_id, comment)
    # Clear cache after adding comment
    get_ticket_comments.clear()
    return result


def get_users_list():
    """Get list of users for assignment"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_users()


def ticket_action(action, ticket_id, **kwargs):
    """Perform ticket action"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL

    if action == 'approve':
        result = api.approve_ticket(ticket_id)
    elif action == 'reject':
        result = api.reject_ticket(ticket_id, kwargs.get('reason', ''))
    elif action == 'assign':
        result = api.assign_ticket(ticket_id, kwargs.get('user_id'))
    elif action == 'start':
        result = api.start_ticket(ticket_id)
    elif action == 'complete':
        result = api.complete_ticket(ticket_id)
    else:
        raise Exception(f"Unknown action: {action}")

    # Clear tickets cache
    get_tickets.clear()
    return result


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

                # Action Buttons based on status and role
                user_role = st.session_state.get('user_role', 'member')
                user_id = st.session_state.get('user_id')
                is_manager = user_role in ['admin', 'manager']
                is_assigned = assigned and assigned.get('id') == user_id

                st.markdown("---")
                st.markdown("**⚡ Actions**")

                action_cols = st.columns(4)

                # REQUESTED → Manager can Approve or Reject
                if status == 'requested' and is_manager:
                    with action_cols[0]:
                        if st.button("✅ Approve", key=f"approve_{ticket_id}", use_container_width=True):
                            try:
                                ticket_action('approve', ticket_id)
                                st.success("Ticket approved!")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                    with action_cols[1]:
                        if st.button("❌ Reject", key=f"reject_{ticket_id}", use_container_width=True):
                            st.session_state[f"show_reject_{ticket_id}"] = True

                    if st.session_state.get(f"show_reject_{ticket_id}"):
                        reason = st.text_input("Rejection reason", key=f"reject_reason_{ticket_id}")
                        if st.button("Confirm Reject", key=f"confirm_reject_{ticket_id}"):
                            try:
                                ticket_action('reject', ticket_id, reason=reason)
                                st.session_state[f"show_reject_{ticket_id}"] = False
                                st.success("Ticket rejected!")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

                # APPROVED → Manager can Assign
                elif status == 'approved' and is_manager:
                    with action_cols[0]:
                        users = get_users_list()
                        if not isinstance(users, list):
                            users = users.get('results', []) if isinstance(users, dict) else []
                        user_options = {u['id']: f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u['username'] for u in users}

                        selected_user = st.selectbox(
                            "Assign to",
                            options=list(user_options.keys()),
                            format_func=lambda x: user_options.get(x, 'Unknown'),
                            key=f"assign_select_{ticket_id}"
                        )
                    with action_cols[1]:
                        if st.button("👤 Assign", key=f"assign_{ticket_id}", use_container_width=True):
                            try:
                                ticket_action('assign', ticket_id, user_id=selected_user)
                                st.success("Ticket assigned!")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

                # IN_PROGRESS → Assigned user or Manager can Complete
                elif status == 'in_progress' and (is_assigned or is_manager):
                    with action_cols[0]:
                        if st.button("✅ Complete", key=f"complete_{ticket_id}", use_container_width=True, type="primary"):
                            try:
                                ticket_action('complete', ticket_id)
                                st.success("Ticket completed!")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

                # APPROVED with assignment → Assigned user can Start
                elif status == 'approved' and is_assigned:
                    with action_cols[0]:
                        if st.button("🚀 Start Work", key=f"start_{ticket_id}", use_container_width=True, type="primary"):
                            try:
                                ticket_action('start', ticket_id)
                                st.success("Work started!")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

                # Show status message for completed/rejected
                elif status == 'completed':
                    st.success("✅ This ticket has been completed")
                elif status == 'rejected':
                    st.error("❌ This ticket was rejected")
                else:
                    st.caption("No actions available for your role")

                st.markdown("---")

                # Comments - Load on demand
                st.markdown("**💬 Comments**")

                # Initialize session state for this ticket's comments
                comments_key = f"show_comments_{ticket_id}"
                if comments_key not in st.session_state:
                    st.session_state[comments_key] = False

                col_btn, col_space = st.columns([1, 3])
                with col_btn:
                    if st.button("📥 Load Comments", key=f"load_{ticket_id}", use_container_width=True):
                        st.session_state[comments_key] = True

                if st.session_state[comments_key]:
                    try:
                        comments = get_ticket_comments(token, ticket_id)
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
                                st.session_state[comments_key] = True
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
