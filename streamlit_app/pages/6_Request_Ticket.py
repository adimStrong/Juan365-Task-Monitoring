"""
Request Ticket Page
Create new ticket requests - supports both local and API modes
"""
import streamlit as st
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEPLOYMENT_MODE = os.getenv('DEPLOYMENT_MODE', 'local')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000/api')

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
st.markdown("---")


def get_users_for_assignment():
    """Get users for assignment dropdown"""
    if DEPLOYMENT_MODE == 'api':
        from utils.api_client import get_api_client
        api = get_api_client()
        try:
            return api.get_users()
        except:
            return []
    else:
        from utils.db import get_all_users
        return list(get_all_users())


def create_ticket_request(title, description, priority, deadline, assigned_to_id):
    """Create a ticket"""
    if DEPLOYMENT_MODE == 'api':
        from utils.api_client import get_api_client
        api = get_api_client()
        deadline_str = deadline.isoformat() if deadline else None
        return api.create_ticket(title, description, priority, deadline_str, assigned_to_id)
    else:
        from utils.db import create_ticket
        deadline_dt = datetime.combine(deadline, datetime.max.time()) if deadline else None
        ticket = create_ticket(
            title=title,
            description=description,
            priority=priority,
            deadline=deadline_dt,
            requester_id=st.session_state.user_id,
            assigned_to_id=assigned_to_id
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
        try:
            users = get_users_for_assignment()
            if users:
                user_options = {}
                user_ids = [None]
                for u in users:
                    if isinstance(u, dict):
                        uid = u.get('id')
                        name = f"{u.get('first_name', '')} {u.get('last_name', '')} (@{u.get('username', '')})"
                    else:
                        uid = u['id']
                        name = f"{u['first_name']} {u['last_name']} (@{u['username']})"
                    user_options[uid] = name.strip()
                    user_ids.append(uid)

                user_options[None] = "-- Manager will assign --"

                assigned_to = st.selectbox(
                    "Assign To (Optional)",
                    options=user_ids,
                    format_func=lambda x: user_options.get(x, "Unknown")
                )
            else:
                assigned_to = None
                st.info("No users available")
        except Exception as e:
            assigned_to = None
            st.caption(f"Could not load users: {e}")

        deadline = st.date_input(
            "Deadline (Optional)",
            value=None,
            min_value=datetime.now().date(),
            format="YYYY-MM-DD"
        )

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
                    deadline=deadline,
                    assigned_to_id=assigned_to
                )

                ticket_id = result.get('id') if isinstance(result, dict) else result.id

                st.success(f"✅ Ticket #{ticket_id} created successfully!")
                st.balloons()

                st.markdown("---")
                st.markdown("### Your Ticket Details")
                st.markdown(f"**Ticket ID:** #{ticket_id}")
                st.markdown(f"**Title:** {title}")
                st.markdown(f"**Status:** 🔵 Requested")
                st.markdown(f"**Priority:** {priority.title()}")

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
    - 🟢 **Low** - Nice to have
    - 🟡 **Medium** - Standard request
    - 🟠 **High** - Important, needs attention
    - 🔥 **Urgent** - Critical, immediate attention needed
    """)
