"""
Request Ticket Page
Create new ticket requests - supports both local and API modes
"""
import streamlit as st
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get configuration from secrets or environment
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
    page_title="Request Ticket - Juan365",
    page_icon="➕",
    layout="wide"
)

# Check login
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
    if st.button("📋 My Tickets", use_container_width=True):
        st.switch_page("pages/7_My_Tickets.py")
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.switch_page("app.py")

# Main content
st.title("➕ Request New Ticket")
st.markdown("Submit a new task request to the team.")
st.info("📝 After submission, a manager will review and approve your request, then assign it to a team member.")
st.markdown("---")


def create_ticket_request(title, description, priority, deadline):
    """Create a ticket"""
    if DEPLOYMENT_MODE == 'api':
        from utils.api_client import get_api_client
        api = get_api_client()
        api.base_url = API_BASE_URL
        deadline_str = deadline.isoformat() if deadline else None
        return api.create_ticket(title, description, priority, deadline_str)
    else:
        from utils.db import create_ticket
        deadline_dt = datetime.combine(deadline, datetime.max.time()) if deadline else None
        ticket = create_ticket(
            title=title,
            description=description,
            priority=priority,
            deadline=deadline_dt,
            requester_id=st.session_state.user_id
        )
        return {'id': ticket.id, 'title': ticket.title, 'status': ticket.status}


# Ticket form
with st.form("ticket_form"):
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

        st.caption("💡 Assignment will be done by manager after approval")

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
            st.switch_page("app.py")

    if submit:
        if not title:
            st.error("Please enter a title")
        elif not description:
            st.error("Please enter a description")
        else:
            try:
                result = create_ticket_request(
                    title=title,
                    description=description,
                    priority=priority,
                    deadline=deadline
                )

                ticket_id = result.get('id') if isinstance(result, dict) else result.id

                st.success(f"✅ Ticket #{ticket_id} created successfully!")
                st.balloons()

                st.markdown("---")
                st.markdown("### Your Ticket Details")
                st.markdown(f"**Ticket ID:** #{ticket_id}")
                st.markdown(f"**Title:** {title}")
                st.markdown(f"**Status:** 🔵 Requested (Pending Approval)")
                st.markdown(f"**Priority:** {priority.title()}")
                if deadline:
                    st.markdown(f"**Deadline:** {deadline}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📋 View My Tickets"):
                        st.switch_page("pages/7_My_Tickets.py")
                with col2:
                    if st.button("➕ Create Another"):
                        st.rerun()

            except Exception as e:
                st.error(f"Error creating ticket: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

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
