"""
Request Ticket Page - Create new ticket requests
"""
import streamlit as st
from datetime import datetime
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
    page_title="New Request - Juan365",
    page_icon="➕",
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
    if st.button("➕ New Request", use_container_width=True, type="primary"):
        st.switch_page("pages/3_Request_Ticket.py")
    if st.button("👥 Activity & Users", use_container_width=True):
        st.switch_page("pages/4_Activity_Users.py")
    if st.button("📝 My Tasks", use_container_width=True):
        st.switch_page("pages/5_My_Tasks.py")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.switch_page("app.py")


def create_ticket(title, description, priority, deadline):
    """Create ticket via API"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    deadline_str = deadline.isoformat() if deadline else None
    return api.create_ticket(title, description, priority, deadline_str)


# Initialize form state
if 'ticket_created' not in st.session_state:
    st.session_state.ticket_created = None
if 'form_key' not in st.session_state:
    st.session_state.form_key = 0

# Main content
st.title("➕ Request New Ticket")

# Show success message if ticket was just created
if st.session_state.ticket_created:
    ticket = st.session_state.ticket_created
    st.success(f"✅ Ticket #{ticket['id']} created successfully!")
    st.balloons()

    st.markdown("---")
    st.markdown("### Your Ticket Details")
    st.markdown(f"**Ticket ID:** #{ticket['id']}")
    st.markdown(f"**Title:** {ticket['title']}")
    st.markdown(f"**Status:** 🔵 Requested (Pending Approval)")
    st.markdown(f"**Priority:** {ticket['priority'].title()}")
    if ticket.get('deadline'):
        st.markdown(f"**Deadline:** {ticket['deadline']}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 View All Tickets", use_container_width=True):
            st.session_state.ticket_created = None
            st.switch_page("pages/2_Tickets.py")
    with col2:
        if st.button("➕ Create Another Ticket", use_container_width=True, type="primary"):
            st.session_state.ticket_created = None
            st.session_state.form_key += 1
            st.rerun()
    st.stop()

st.info("📝 After submission, a manager will review and approve your request, then assign it to a team member.")
st.markdown("---")

# Ticket form with dynamic key to reset fields
with st.form(f"ticket_form_{st.session_state.form_key}"):
    col1, col2 = st.columns(2)

    with col1:
        title = st.text_input(
            "Title *",
            placeholder="Brief description of your request",
            max_chars=200
        )

        priority = st.selectbox(
            "Priority *",
            options=["medium", "low", "high", "urgent"],
            format_func=lambda x: {
                'low': '🟢 Low',
                'medium': '🟡 Medium',
                'high': '🟠 High',
                'urgent': '🔥 Urgent'
            }.get(x, x)
        )

    with col2:
        deadline = st.date_input(
            "Deadline (Optional)",
            value=None,
            min_value=datetime.now().date(),
            format="YYYY-MM-DD"
        )
        st.caption("💡 Same-day deadline only for Urgent priority")
        st.caption("📋 Assignment done by manager after approval")

    description = st.text_area(
        "Description *",
        placeholder="Provide detailed information about your request...\n\n- What do you need?\n- Why is it needed?\n- Any specific requirements?",
        height=200
    )

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        submit = st.form_submit_button("📤 Submit Request", type="primary", use_container_width=True)
    with col2:
        if st.form_submit_button("❌ Cancel", use_container_width=True):
            st.switch_page("pages/1_Dashboard.py")

    if submit:
        if not title:
            st.error("Please enter a title")
        elif not description:
            st.error("Please enter a description")
        elif deadline and deadline == datetime.now().date() and priority != 'urgent':
            st.error("⚠️ Same-day deadline is only allowed for Urgent priority tickets. Please select a future date or change priority to Urgent.")
        else:
            try:
                result = create_ticket(
                    title=title,
                    description=description,
                    priority=priority,
                    deadline=deadline
                )

                ticket_id = result.get('id') if isinstance(result, dict) else result.id

                # Store created ticket info and reset form
                st.session_state.ticket_created = {
                    'id': ticket_id,
                    'title': title,
                    'priority': priority,
                    'deadline': str(deadline) if deadline else None
                }
                st.session_state.form_key += 1
                st.rerun()

            except Exception as e:
                st.error(f"Error creating ticket: {str(e)}")

# Tips
with st.expander("💡 Tips for a good ticket request"):
    st.markdown("""
    **Title:** Be specific and concise (e.g., "Update homepage banner for Christmas")

    **Priority:**
    - 🟢 **Low** - Nice to have, no rush
    - 🟡 **Medium** - Standard request
    - 🟠 **High** - Important, needs attention soon
    - 🔥 **Urgent** - Critical, immediate attention needed

    **Workflow:**
    1. 📝 You submit a request
    2. ✅ Manager reviews and approves
    3. 👤 Manager assigns to team member
    4. 🚀 Work begins
    5. ✅ Task completed
    """)
