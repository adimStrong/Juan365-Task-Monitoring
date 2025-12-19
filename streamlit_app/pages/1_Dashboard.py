"""
Dashboard Page - Charts and Statistics
"""
import streamlit as st
import os
import sys

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
    page_title="Dashboard - Juan365",
    page_icon="📊",
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
    st.image("assets/logo.jpg", width=150)
    st.markdown(f"### 👤 {st.session_state.get('user_name', 'User')}")
    st.caption(f"@{st.session_state.get('username', '')} • {(st.session_state.get('user_role') or 'User').title()}")
    st.markdown("---")

    if st.button("📊 Dashboard", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Dashboard.py")
    if st.button("📋 Tickets", use_container_width=True):
        st.switch_page("pages/2_Tickets.py")
    if st.button("➕ New Request", use_container_width=True):
        st.switch_page("pages/3_Request_Ticket.py")
    if st.button("👥 Activity & Users", use_container_width=True):
        st.switch_page("pages/4_Activity_Users.py")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.switch_page("app.py")


def get_dashboard_stats():
    """Get dashboard statistics from API"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    try:
        return api.get_dashboard_stats()
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        return {}


def get_my_tasks():
    """Get user's assigned tasks"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL
    try:
        return api.get_my_tasks()
    except:
        return []


# Main content
st.title("📊 Dashboard")
st.markdown(f"Welcome back, **{st.session_state.get('user_name', 'User')}**!")
st.markdown("---")

try:
    stats = get_dashboard_stats()

    # Stats Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📋 Total Tickets",
            value=stats.get('total_tickets', 0)
        )
    with col2:
        st.metric(
            label="⏳ Pending Approval",
            value=stats.get('pending_approval', 0)
        )
    with col3:
        st.metric(
            label="🔄 In Progress",
            value=stats.get('in_progress', 0)
        )
    with col4:
        st.metric(
            label="⚠️ Overdue",
            value=stats.get('overdue', 0),
            delta=None if stats.get('overdue', 0) == 0 else "needs attention",
            delta_color="inverse"
        )

    st.markdown("---")

    # Charts Row
    col1, col2, col3 = st.columns(3)

    # Status Pie Chart
    with col1:
        st.markdown("### Tickets by Status")
        status_data = stats.get('status_chart', [])
        if status_data:
            import pandas as pd
            df_status = pd.DataFrame(status_data)
            if not df_status.empty and 'value' in df_status.columns:
                df_status = df_status[df_status['value'] > 0]
                if not df_status.empty:
                    st.bar_chart(df_status.set_index('name')['value'])
                else:
                    st.info("No tickets yet")
        else:
            st.info("No data available")

    # Priority Bar Chart
    with col2:
        st.markdown("### Tickets by Priority")
        priority_data = stats.get('priority_chart', [])
        if priority_data:
            import pandas as pd
            df_priority = pd.DataFrame(priority_data)
            if not df_priority.empty and 'count' in df_priority.columns:
                st.bar_chart(df_priority.set_index('name')['count'])
            else:
                st.info("No data available")
        else:
            st.info("No data available")

    # Weekly Trends
    with col3:
        st.markdown("### Weekly Trends")
        weekly_data = stats.get('weekly_chart', [])
        if weekly_data:
            import pandas as pd
            df_weekly = pd.DataFrame(weekly_data)
            if not df_weekly.empty:
                st.line_chart(df_weekly.set_index('day')[['created', 'completed']])
            else:
                st.info("No data available")
        else:
            st.info("No data available")

    st.markdown("---")

    # Quick Actions & My Tasks
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### ⚡ Quick Actions")
        if st.button("➕ Create New Ticket", use_container_width=True, type="primary"):
            st.switch_page("pages/3_Request_Ticket.py")
        if st.button("📋 View All Tickets", use_container_width=True):
            st.switch_page("pages/2_Tickets.py")

        is_manager = st.session_state.get('user_role') in ['admin', 'manager']
        if is_manager and stats.get('pending_approval', 0) > 0:
            if st.button(f"🔍 Review Pending ({stats.get('pending_approval', 0)})", use_container_width=True):
                st.switch_page("pages/2_Tickets.py")

    with col2:
        st.markdown("### 📝 My Tasks")
        tasks = get_my_tasks()

        if not tasks:
            st.info("No tasks assigned to you.")
        else:
            if isinstance(tasks, dict):
                tasks = tasks.get('results', [])

            for task in tasks[:5]:
                status_emoji = {
                    'requested': '🔵', 'approved': '🟢', 'in_progress': '🟡',
                    'completed': '✅', 'rejected': '🔴'
                }.get(task.get('status'), '⚪')

                priority_color = {
                    'urgent': '🔥', 'high': '🟠', 'medium': '🟡', 'low': '🟢'
                }.get(task.get('priority'), '')

                with st.container():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"{status_emoji} **#{task.get('id')}** - {task.get('title')}")
                        requester = task.get('requester', {})
                        st.caption(f"From: {requester.get('first_name', '')} {requester.get('last_name', '')}")
                    with col_b:
                        st.caption(f"{priority_color} {task.get('priority', '').title()}")
                        if task.get('is_overdue'):
                            st.error("Overdue!")

except Exception as e:
    st.error(f"Error loading dashboard: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
