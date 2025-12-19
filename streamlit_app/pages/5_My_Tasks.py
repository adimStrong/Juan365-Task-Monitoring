"""
My Tasks Page - View tasks assigned to current user
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
    page_title="My Tasks - Juan365",
    page_icon="📝",
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
    if st.button("👥 Activity & Users", use_container_width=True):
        st.switch_page("pages/4_Activity_Users.py")
    if st.button("📝 My Tasks", use_container_width=True, type="primary"):
        st.switch_page("pages/5_My_Tasks.py")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.switch_page("app.py")


def get_my_tasks():
    """Get tasks assigned to current user"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_my_tasks()


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
st.title("📝 My Tasks")
st.markdown("Tasks assigned to you that need attention")
st.markdown("---")

try:
    tasks = get_my_tasks()

    if isinstance(tasks, dict):
        tasks = tasks.get('results', [])

    if not tasks:
        st.info("🎉 No tasks assigned to you! You're all caught up.")
        if st.button("📋 View All Tickets"):
            st.switch_page("pages/2_Tickets.py")
    else:
        st.caption(f"You have **{len(tasks)}** active task(s)")

        for task in tasks:
            ticket_id = task.get('id')
            title = task.get('title')
            status = task.get('status')
            priority = task.get('priority')
            description = task.get('description', '')
            requester = task.get('requester', {})
            requester_name = f"{requester.get('first_name', '')} {requester.get('last_name', '')}".strip() or requester.get('username', 'Unknown')
            created_at = task.get('created_at', '')[:16].replace('T', ' ')
            deadline = task.get('deadline', '')[:10] if task.get('deadline') else None
            is_overdue = task.get('is_overdue', False)

            status_emoji = {
                'requested': '🔵', 'approved': '🟢', 'in_progress': '🟡',
                'completed': '✅', 'rejected': '🔴'
            }.get(status, '⚪')

            priority_emoji = {
                'urgent': '🔥', 'high': '🟠', 'medium': '🟡', 'low': '🟢'
            }.get(priority, '')

            # Card style
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    expander_label = f"{status_emoji} {priority_emoji} **#{ticket_id} - {title}**"
                    if is_overdue:
                        expander_label += " ⚠️ OVERDUE"

                with col2:
                    if deadline:
                        st.caption(f"📆 {deadline}")

            with st.expander(expander_label, expanded=False):
                # Info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**Status**")
                    st.write(f"{status_emoji} {status.replace('_', ' ').title() if status else '-'}")
                with col2:
                    st.markdown("**Priority**")
                    st.write(f"{priority_emoji} {priority.title() if priority else '-'}")
                with col3:
                    st.markdown("**From**")
                    st.write(f"👤 {requester_name}")

                if is_overdue:
                    st.error("⚠️ This task is overdue!")

                st.markdown("---")

                # Description
                st.markdown("**Description**")
                st.text_area("", value=description, height=80, disabled=True, key=f"desc_{ticket_id}", label_visibility="collapsed")

                st.caption(f"📅 Created: {created_at}")

                st.markdown("---")

                # Comments
                st.markdown("**💬 Comments**")
                try:
                    comments = get_ticket_comments(ticket_id)
                    if not isinstance(comments, list):
                        comments = comments.get('results', []) if isinstance(comments, dict) else []

                    if comments:
                        for comment in comments[-5:]:  # Show last 5 comments
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
                with st.form(f"task_comment_{ticket_id}"):
                    new_comment = st.text_input("Add comment", placeholder="Update on this task...", key=f"task_input_{ticket_id}")
                    if st.form_submit_button("💬 Send"):
                        if new_comment:
                            try:
                                add_comment(ticket_id, new_comment)
                                st.success("Comment added!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

except Exception as e:
    st.error(f"Error loading tasks: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
