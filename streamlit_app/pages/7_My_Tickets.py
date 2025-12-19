"""
My Tickets Page
View and manage your tickets
"""
import streamlit as st
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        st.switch_page("pages/6_Request_Ticket.py")

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.switch_page("app.py")

# Main content
st.title("📋 My Tickets")

# Filters
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    search = st.text_input("🔍 Search", placeholder="Search tickets...")
with col2:
    status_filter = st.selectbox(
        "Status",
        options=["all", "requested", "approved", "in_progress", "completed", "rejected"],
        format_func=lambda x: x.replace("_", " ").title() if x != "all" else "All Status"
    )
with col3:
    view_mode = st.selectbox("View", ["My Requests", "Assigned to Me", "All My Tickets"])

st.markdown("---")

try:
    from utils.db import get_user_tickets, get_ticket_comments, add_ticket_comment, get_ticket_attachments
    from django.db.models import Q

    # Get tickets based on view mode
    if view_mode == "My Requests":
        from api.models import Ticket
        tickets = Ticket.objects.filter(requester_id=st.session_state.user_id)
    elif view_mode == "Assigned to Me":
        from api.models import Ticket
        tickets = Ticket.objects.filter(assigned_to_id=st.session_state.user_id)
    else:
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
            status_emoji = {
                'requested': '🔵',
                'approved': '🟢',
                'in_progress': '🟡',
                'completed': '✅',
                'rejected': '🔴'
            }.get(ticket.status, '⚪')

            priority_emoji = {
                'urgent': '🔥',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(ticket.priority, '')

            with st.expander(f"{status_emoji} {priority_emoji} **#{ticket.id} - {ticket.title}**", expanded=False):
                # Header info
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.markdown("**Status**")
                    st.write(f"{status_emoji} {ticket.get_status_display()}")
                with col2:
                    st.markdown("**Priority**")
                    st.write(f"{priority_emoji} {ticket.get_priority_display()}")
                with col3:
                    st.markdown("**Requester**")
                    if ticket.requester:
                        st.write(f"👤 {ticket.requester.first_name} {ticket.requester.last_name}")
                with col4:
                    st.markdown("**Assigned To**")
                    if ticket.assigned_to:
                        st.write(f"👤 {ticket.assigned_to.first_name} {ticket.assigned_to.last_name}")
                    else:
                        st.write("⚠️ Unassigned")

                st.markdown("---")

                # Description
                st.markdown("**Description**")
                st.text_area(
                    "desc",
                    value=ticket.description,
                    height=100,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"desc_{ticket.id}"
                )

                # Dates
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption(f"📅 Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M')}")
                with col2:
                    st.caption(f"🔄 Updated: {ticket.updated_at.strftime('%Y-%m-%d %H:%M')}")
                with col3:
                    if ticket.deadline:
                        from django.utils import timezone
                        if ticket.deadline < timezone.now() and ticket.status not in ['completed', 'rejected']:
                            st.caption(f"🚨 Deadline: {ticket.deadline.strftime('%Y-%m-%d')} (OVERDUE)")
                        else:
                            st.caption(f"📆 Deadline: {ticket.deadline.strftime('%Y-%m-%d')}")

                st.markdown("---")

                # Comments section
                st.markdown("**💬 Comments**")

                comments = list(get_ticket_comments(ticket.id))
                if comments:
                    for comment in comments:
                        st.markdown(f"**{comment.user.first_name}** - {comment.created_at.strftime('%m/%d %H:%M')}")
                        st.caption(comment.comment)

                        # Show replies
                        for reply in comment.replies.all():
                            st.markdown(f"↳ **{reply.user.first_name}** - {reply.created_at.strftime('%m/%d %H:%M')}")
                            st.caption(reply.comment)
                else:
                    st.caption("No comments yet")

                # Add comment form
                with st.form(f"comment_form_{ticket.id}"):
                    new_comment = st.text_input("Add a comment", placeholder="Type your comment...", key=f"comment_input_{ticket.id}")
                    if st.form_submit_button("💬 Send", key=f"send_comment_{ticket.id}"):
                        if new_comment:
                            try:
                                add_ticket_comment(ticket.id, st.session_state.user_id, new_comment)
                                st.success("Comment added!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

                # Attachments
                st.markdown("---")
                st.markdown("**📎 Attachments**")
                attachments = list(get_ticket_attachments(ticket.id))
                if attachments:
                    for att in attachments:
                        st.write(f"📄 {att.file_name}")
                else:
                    st.caption("No attachments")

    else:
        st.info("No tickets found. Create a new request to get started!")
        if st.button("➕ Create New Request"):
            st.switch_page("pages/6_Request_Ticket.py")

except Exception as e:
    st.error(f"Error loading tickets: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
