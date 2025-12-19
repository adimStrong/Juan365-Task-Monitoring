"""
Ticket Detail Page - View and manage a single ticket
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
    page_title="Ticket Detail - Juan365",
    page_icon="🎫",
    layout="wide"
)

# Check login
if not st.session_state.get('logged_in', False):
    st.warning("Please login first")
    if st.button("Go to Login"):
        st.switch_page("app.py")
    st.stop()

# Check if ticket_id is set
if 'view_ticket_id' not in st.session_state or not st.session_state.view_ticket_id:
    st.warning("No ticket selected")
    if st.button("← Back to Tickets"):
        st.switch_page("pages/2_Tickets.py")
    st.stop()

ticket_id = st.session_state.view_ticket_id

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
    if st.button("📝 My Tasks", use_container_width=True):
        st.switch_page("pages/5_My_Tasks.py")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.switch_page("app.py")


# API Functions
def get_ticket(ticket_id):
    """Get single ticket details"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.get_ticket(ticket_id)


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


def upload_attachment(ticket_id, file_data, file_name):
    """Upload attachment to ticket"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    return api.upload_attachment(ticket_id, file_data, file_name)


def get_attachments(ticket_id):
    """Get ticket attachments"""
    import requests
    headers = {'Content-Type': 'application/json'}
    token = st.session_state.get('api_token')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        response = requests.get(f"{API_BASE_URL}/tickets/{ticket_id}/attachments/", headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except:
        return []


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
        return api.approve_ticket(ticket_id)
    elif action == 'reject':
        return api.reject_ticket(ticket_id, kwargs.get('reason', ''))
    elif action == 'assign':
        return api.assign_ticket(ticket_id, kwargs.get('user_id'))
    elif action == 'start':
        return api.start_ticket(ticket_id)
    elif action == 'complete':
        return api.complete_ticket(ticket_id)
    else:
        raise Exception(f"Unknown action: {action}")


# Load ticket data
try:
    ticket = get_ticket(ticket_id)
except Exception as e:
    st.error(f"Error loading ticket: {e}")
    if st.button("← Back to Tickets"):
        st.switch_page("pages/2_Tickets.py")
    st.stop()

# Extract ticket info
title = ticket.get('title', 'Untitled')
status = ticket.get('status', 'unknown')
priority = ticket.get('priority', 'medium')
description = ticket.get('description', '')
requester = ticket.get('requester', {})
requester_name = f"{requester.get('first_name', '')} {requester.get('last_name', '')}".strip() or requester.get('username', 'Unknown')
assigned = ticket.get('assigned_to', {})
assigned_name = f"{assigned.get('first_name', '')} {assigned.get('last_name', '')}".strip() if assigned else None
created_at = ticket.get('created_at', '')[:16].replace('T', ' ')
deadline = ticket.get('deadline', '')[:10] if ticket.get('deadline') else None
rejection_reason = ticket.get('rejection_reason', '')

status_emoji = {
    'requested': '🔵', 'approved': '🟢', 'in_progress': '🟡',
    'completed': '✅', 'rejected': '🔴'
}.get(status, '⚪')

priority_emoji = {
    'urgent': '🔥', 'high': '🟠', 'medium': '🟡', 'low': '🟢'
}.get(priority, '')

status_color = {
    'requested': 'blue', 'approved': 'green', 'in_progress': 'orange',
    'completed': 'gray', 'rejected': 'red'
}.get(status, 'gray')

# Header with back button
col_back, col_title = st.columns([1, 5])
with col_back:
    if st.button("← Back", use_container_width=True):
        st.switch_page("pages/2_Tickets.py")
with col_title:
    st.title(f"🎫 Ticket #{ticket_id}")

st.markdown("---")

# Status banner
if status == 'completed':
    st.success(f"✅ This ticket has been completed")
elif status == 'rejected':
    st.error(f"❌ This ticket was rejected" + (f": {rejection_reason}" if rejection_reason else ""))
elif status == 'in_progress':
    st.info(f"🔄 This ticket is in progress")
elif status == 'approved':
    if assigned_name:
        st.info(f"✅ Approved and assigned to {assigned_name}")
    else:
        st.warning(f"✅ Approved - Waiting for assignment")
elif status == 'requested':
    st.warning(f"⏳ Waiting for approval")

# Main content in two columns
col1, col2 = st.columns([2, 1])

with col1:
    # Ticket Info Card
    st.markdown("### 📋 Ticket Details")

    st.markdown(f"**Title:** {title}")
    st.markdown(f"**Description:**")
    st.text_area("", value=description, height=150, disabled=True, key="desc_view", label_visibility="collapsed")

    st.markdown("---")

    # Comments Section
    st.markdown("### 💬 Comments")

    try:
        comments = get_ticket_comments(ticket_id)
        if not isinstance(comments, list):
            comments = comments.get('results', []) if isinstance(comments, dict) else []

        if comments:
            for comment in comments:
                user_info = comment.get('user', {})
                user_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() or user_info.get('username', 'User')
                comment_time = comment.get('created_at', '')[:16].replace('T', ' ')

                with st.container():
                    st.markdown(f"**{user_name}** • {comment_time}")
                    st.caption(comment.get('comment', ''))
                    st.markdown("---")
        else:
            st.caption("No comments yet")
    except:
        st.caption("Could not load comments")

    # Add comment form
    with st.form("add_comment_form"):
        new_comment = st.text_area("Add a comment", placeholder="Type your comment here...", height=100)
        if st.form_submit_button("💬 Post Comment", use_container_width=True):
            if new_comment:
                try:
                    add_comment(ticket_id, new_comment)
                    st.success("Comment added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please enter a comment")

    st.markdown("---")

    # Attachments Section
    st.markdown("### 📎 Attachments")

    try:
        attachments = get_attachments(ticket_id)
        if not isinstance(attachments, list):
            attachments = attachments.get('results', []) if isinstance(attachments, dict) else []

        if attachments:
            for att in attachments:
                file_name = att.get('file_name', 'Unknown file')
                file_url = att.get('file', '')
                uploaded_by = att.get('user', {})
                uploader_name = f"{uploaded_by.get('first_name', '')} {uploaded_by.get('last_name', '')}".strip() or uploaded_by.get('username', 'User')
                uploaded_at = att.get('uploaded_at', '')[:16].replace('T', ' ')

                col_file, col_info = st.columns([3, 1])
                with col_file:
                    st.markdown(f"📄 **{file_name}**")
                    st.caption(f"Uploaded by {uploader_name} • {uploaded_at}")
                with col_info:
                    if file_url:
                        st.markdown(f"[Download]({file_url})")
        else:
            st.caption("No attachments yet")
    except:
        st.caption("Could not load attachments")

    # Upload attachment
    st.markdown("**Upload File**")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'gif', 'txt', 'csv', 'zip'],
        key="file_upload",
        label_visibility="collapsed"
    )

    if uploaded_file:
        if st.button("📤 Upload Attachment", use_container_width=True):
            try:
                upload_attachment(ticket_id, uploaded_file.getvalue(), uploaded_file.name)
                st.success(f"File '{uploaded_file.name}' uploaded!")
                st.rerun()
            except Exception as e:
                st.error(f"Upload error: {e}")

with col2:
    # Info sidebar
    st.markdown("### 📊 Status")
    st.markdown(f"**{status_emoji} {status.replace('_', ' ').title()}**")

    st.markdown("---")

    st.markdown("### 🎯 Priority")
    st.markdown(f"**{priority_emoji} {priority.title()}**")

    st.markdown("---")

    st.markdown("### 👤 People")
    st.markdown(f"**Requester:** {requester_name}")
    st.markdown(f"**Assigned:** {assigned_name if assigned_name else '⚠️ Unassigned'}")

    st.markdown("---")

    st.markdown("### 📅 Dates")
    st.markdown(f"**Created:** {created_at}")
    if deadline:
        st.markdown(f"**Deadline:** {deadline}")

    st.markdown("---")

    # Action Buttons
    st.markdown("### ⚡ Actions")

    user_role = st.session_state.get('user_role', 'member')
    current_user_id = st.session_state.get('user_id')
    is_manager = user_role in ['admin', 'manager']
    is_assigned = assigned and assigned.get('id') == current_user_id

    # REQUESTED → Manager can Approve or Reject
    if status == 'requested' and is_manager:
        if st.button("✅ Approve", key="approve_btn", use_container_width=True, type="primary"):
            try:
                ticket_action('approve', ticket_id)
                st.success("Ticket approved!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        if st.button("❌ Reject", key="reject_btn", use_container_width=True):
            st.session_state.show_reject_form = True

        if st.session_state.get('show_reject_form'):
            reason = st.text_input("Rejection reason")
            if st.button("Confirm Reject", key="confirm_reject"):
                try:
                    ticket_action('reject', ticket_id, reason=reason)
                    st.session_state.show_reject_form = False
                    st.success("Ticket rejected!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    # APPROVED → Manager can Assign
    elif status == 'approved' and is_manager and not assigned_name:
        users = get_users_list()
        if not isinstance(users, list):
            users = users.get('results', []) if isinstance(users, dict) else []
        user_options = {u['id']: f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u['username'] for u in users}

        selected_user = st.selectbox(
            "Assign to",
            options=list(user_options.keys()),
            format_func=lambda x: user_options.get(x, 'Unknown'),
            key="assign_select"
        )

        if st.button("👤 Assign", key="assign_btn", use_container_width=True, type="primary"):
            try:
                ticket_action('assign', ticket_id, user_id=selected_user)
                st.success("Ticket assigned!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    # APPROVED with assignment → Assigned user can Start
    elif status == 'approved' and is_assigned:
        if st.button("🚀 Start Work", key="start_btn", use_container_width=True, type="primary"):
            try:
                ticket_action('start', ticket_id)
                st.success("Work started!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    # IN_PROGRESS → Assigned user or Manager can Complete
    elif status == 'in_progress' and (is_assigned or is_manager):
        if st.button("✅ Mark Complete", key="complete_btn", use_container_width=True, type="primary"):
            try:
                ticket_action('complete', ticket_id)
                st.success("Ticket completed!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    elif status in ['completed', 'rejected']:
        st.caption("No actions available")
    else:
        st.caption("No actions available for your role")
