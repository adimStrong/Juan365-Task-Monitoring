"""
Tickets Page
View tickets with their files and full details
"""
import streamlit as st
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_all_tickets, get_all_files
from config import MEDIA_ROOT

st.set_page_config(
    page_title="Tickets - Juan365",
    page_icon="\U0001F3AB",
    layout="wide"
)

st.title("\U0001F3AB Tickets & Files")
st.markdown("View tickets from the ticketing system with their associated files.")

# Filters
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    search = st.text_input("Search tickets...", placeholder="Enter ticket title or ID...")

with col2:
    status_filter = st.selectbox(
        "Status",
        options=["all", "requested", "approved", "in_progress", "completed", "rejected"],
        format_func=lambda x: x.replace("_", " ").title() if x != "all" else "All Status"
    )

with col3:
    priority_filter = st.selectbox(
        "Priority",
        options=["all", "urgent", "high", "medium", "low"],
        format_func=lambda x: x.title() if x != "all" else "All Priority"
    )

st.markdown("---")

try:
    tickets = list(get_all_tickets())

    # Apply filters
    if search:
        tickets = [t for t in tickets if search.lower() in t.title.lower() or search in str(t.id)]

    if status_filter != "all":
        tickets = [t for t in tickets if t.status == status_filter]

    if priority_filter != "all":
        tickets = [t for t in tickets if t.priority == priority_filter]

    st.caption(f"Found {len(tickets)} ticket(s)")

    if tickets:
        for ticket in tickets:
            # Status and priority icons
            status_icon = {
                'requested': '\U0001F7E1',  # yellow
                'approved': '\U0001F7E2',   # green
                'in_progress': '\U0001F535', # blue
                'completed': '\U00002705',   # check
                'rejected': '\U0001F534'     # red
            }.get(ticket.status, '\U000026AA')

            priority_icon = {
                'urgent': '\U0001F525',  # fire
                'high': '\U0001F7E0',    # orange
                'medium': '\U0001F7E1',  # yellow
                'low': '\U0001F7E2'      # green
            }.get(ticket.priority, '')

            # Ticket card
            with st.expander(f"{status_icon} {priority_icon} **#{ticket.id} - {ticket.title}**", expanded=False):
                # Header row
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.markdown("**Status**")
                    st.write(f"{status_icon} {ticket.get_status_display()}")

                with col2:
                    st.markdown("**Priority**")
                    st.write(f"{priority_icon} {ticket.get_priority_display()}")

                with col3:
                    st.markdown("**Requester**")
                    if ticket.requester:
                        st.write(f"\U0001F464 {ticket.requester.first_name} {ticket.requester.last_name}")
                        st.caption(f"@{ticket.requester.username}")
                    else:
                        st.write("Unknown")

                with col4:
                    st.markdown("**Assigned To**")
                    if ticket.assigned_to:
                        st.write(f"\U0001F464 {ticket.assigned_to.first_name} {ticket.assigned_to.last_name}")
                        st.caption(f"@{ticket.assigned_to.username}")
                    else:
                        st.write("\U000026A0 Unassigned")

                st.markdown("---")

                # Description
                st.markdown("**Description**")
                st.text_area(
                    "desc",
                    value=ticket.description or "No description",
                    height=100,
                    disabled=True,
                    label_visibility="collapsed"
                )

                # Dates
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**Created**")
                    st.write(f"\U0001F4C5 {ticket.created_at.strftime('%Y-%m-%d %H:%M')}")

                with col2:
                    st.markdown("**Updated**")
                    st.write(f"\U0001F504 {ticket.updated_at.strftime('%Y-%m-%d %H:%M')}")

                with col3:
                    st.markdown("**Deadline**")
                    if ticket.deadline:
                        # Check if overdue
                        from django.utils import timezone
                        if ticket.deadline < timezone.now() and ticket.status not in ['completed', 'rejected']:
                            st.write(f"\U0001F6A8 {ticket.deadline.strftime('%Y-%m-%d %H:%M')} (OVERDUE)")
                        else:
                            st.write(f"\U0001F4C6 {ticket.deadline.strftime('%Y-%m-%d %H:%M')}")
                    else:
                        st.write("No deadline set")

                st.markdown("---")

                # Files attached to this ticket
                st.markdown("**\U0001F4CE Attached Files**")

                # Get files linked to this ticket
                ticket_files = list(get_all_files(limit=100))
                ticket_files = [f for f in ticket_files if f.ticket_id == ticket.id]

                if ticket_files:
                    for file in ticket_files:
                        file_col1, file_col2, file_col3 = st.columns([3, 1, 1])

                        with file_col1:
                            icon = {
                                'image': '\U0001F5BC',
                                'video': '\U0001F3AC',
                                'document': '\U0001F4C4',
                                'other': '\U0001F4C1'
                            }.get(file.file_type, '\U0001F4C1')
                            st.write(f"{icon} {file.name}")

                        with file_col2:
                            st.caption(file.file_size_display)

                        with file_col3:
                            # Download button
                            try:
                                file_path = MEDIA_ROOT / file.file.name
                                if file_path.exists():
                                    with open(file_path, 'rb') as f:
                                        st.download_button(
                                            label="\U0001F4E5",
                                            data=f.read(),
                                            file_name=file.name,
                                            mime=file.mime_type or 'application/octet-stream',
                                            key=f"dl_{ticket.id}_{file.id}"
                                        )
                            except Exception:
                                st.caption("N/A")

                        # Show image preview
                        if file.file_type == 'image':
                            try:
                                file_path = MEDIA_ROOT / file.file.name
                                if file_path.exists():
                                    st.image(str(file_path), width=300)
                            except Exception:
                                pass
                else:
                    st.info("No files attached to this ticket. Upload files and link them to this ticket.")

                # Quick upload for this ticket
                st.markdown("---")
                if st.button(f"\U0001F4E4 Upload File for Ticket #{ticket.id}", key=f"upload_{ticket.id}"):
                    st.session_state['preselect_ticket'] = ticket.id
                    st.switch_page("pages/1_Upload.py")

    else:
        st.info("\U0001F3AB No tickets found. Create tickets in the main ticketing system.")

except Exception as e:
    st.error(f"Error loading tickets: {str(e)}")
    st.info("Make sure the Django backend database is accessible.")

# Sidebar stats
with st.sidebar:
    st.markdown("### Ticket Stats")
    try:
        all_tickets = list(get_all_tickets())
        st.metric("Total Tickets", len(all_tickets))
        st.metric("Requested", len([t for t in all_tickets if t.status == 'requested']))
        st.metric("In Progress", len([t for t in all_tickets if t.status == 'in_progress']))
        st.metric("Completed", len([t for t in all_tickets if t.status == 'completed']))
    except Exception:
        pass
