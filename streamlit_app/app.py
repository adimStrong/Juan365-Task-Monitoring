"""
Juan365 Ticket Portal
Main Streamlit application - Login page
"""
import streamlit as st
import os
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
LOGO_PATH = SCRIPT_DIR / "assets" / "logo.jpg"

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

# Page configuration
st.set_page_config(
    page_title="Juan365 Ticket Portal",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
    }
    [data-testid="stSidebar"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'api_token' not in st.session_state:
    st.session_state.api_token = None


def login_with_api(username: str, password: str):
    """Login using REST API"""
    from utils.api_client import get_api_client
    api = get_api_client()
    api.base_url = API_BASE_URL

    result = api.login(username, password)
    if 'access' in result:
        st.session_state.api_token = result['access']
        api.set_token(result['access'])

        # Get user info
        user_info = api.get_me()
        st.session_state.logged_in = True
        st.session_state.user_id = user_info.get('id')
        st.session_state.username = user_info.get('username')
        st.session_state.user_role = user_info.get('role', 'member')
        st.session_state.user_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() or username
        return True
    return False


# If already logged in, redirect to dashboard
if st.session_state.logged_in:
    st.switch_page("pages/1_Dashboard.py")

# Login page
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # Logo and title centered using HTML
    import base64

    # Read and encode logo
    with open(LOGO_PATH, "rb") as f:
        logo_data = base64.b64encode(f.read()).decode()

    st.markdown(f"""
        <div style="text-align: center;">
            <img src="data:image/jpeg;base64,{logo_data}" width="180" style="margin-bottom: 10px;">
            <h2 style="margin: 0;">Juan365 Ticket Portal</h2>
            <p style="color: gray; margin-top: 5px;">Task Monitoring & Management System</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    with st.form("login_form"):
        st.markdown("### 🔐 Login")
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        col_a, col_b = st.columns(2)
        with col_a:
            submit = st.form_submit_button("Login", use_container_width=True, type="primary")
        with col_b:
            if st.form_submit_button("Register", use_container_width=True):
                st.info("Please contact your administrator to create an account")

        if submit:
            if username and password:
                try:
                    success = login_with_api(username, password)

                    if success:
                        st.success("Login successful! Redirecting...")
                        st.switch_page("pages/1_Dashboard.py")
                    else:
                        st.error("Invalid credentials or account not approved")
                except Exception as e:
                    st.error(f"Login error: {str(e)}")
            else:
                st.warning("Please enter username and password")

    st.markdown("---")
    st.caption(f"Mode: {DEPLOYMENT_MODE.upper()} | API: {API_BASE_URL}")
