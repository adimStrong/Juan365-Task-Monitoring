"""
Juan365 File Upload Portal
Main Streamlit application entry point
"""
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Juan365 File Portal",
    page_icon="\U0001F4C1",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #3B82F6;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #3B82F6;
    }
    .stat-label {
        color: #6B7280;
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150x50/3B82F6/FFFFFF?text=Juan365", width=150)
    st.markdown("---")
    st.markdown("### Navigation")
    st.markdown("""
    - **Upload** - Upload new files
    - **Browse** - Search and manage files
    - **Gallery** - View images and videos
    - **Documents** - View documents
    """)
    st.markdown("---")
    st.caption("Juan365 File Portal v1.0")

# Main content
st.markdown('<p class="main-header">Juan365 File Portal</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload, manage, and browse your files</p>', unsafe_allow_html=True)

# Initialize database connection
try:
    from utils.db import get_file_stats

    stats = get_file_stats()

    # Dashboard stats
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="\U0001F4C1 Total Files",
            value=stats.get('total_files', 0)
        )

    with col2:
        st.metric(
            label="\U0001F5BC Images",
            value=stats.get('image_count', 0)
        )

    with col3:
        st.metric(
            label="\U0001F3AC Videos",
            value=stats.get('video_count', 0)
        )

    with col4:
        st.metric(
            label="\U0001F4C4 Documents",
            value=stats.get('document_count', 0)
        )

    with col5:
        total_size = stats.get('total_size', 0) or 0
        size_mb = total_size / (1024 * 1024)
        st.metric(
            label="\U0001F4BE Storage Used",
            value=f"{size_mb:.1f} MB"
        )

    st.markdown("---")

    # Quick actions
    st.subheader("Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("\U0001F4E4 Upload Files", use_container_width=True):
            st.switch_page("pages/1_Upload.py")

    with col2:
        if st.button("\U0001F50D Browse Files", use_container_width=True):
            st.switch_page("pages/2_Browse.py")

    with col3:
        if st.button("\U0001F5BC View Gallery", use_container_width=True):
            st.switch_page("pages/3_Gallery.py")

    # Recent files
    st.markdown("---")
    st.subheader("Recent Uploads")

    from utils.db import get_all_files
    recent_files = get_all_files(limit=5)

    if recent_files:
        for file in recent_files:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                icon = {
                    'image': '\U0001F5BC',
                    'video': '\U0001F3AC',
                    'document': '\U0001F4C4',
                    'other': '\U0001F4C1'
                }.get(file.file_type, '\U0001F4C1')
                st.write(f"{icon} {file.name}")
            with col2:
                st.caption(file.file_size_display)
            with col3:
                st.caption(file.created_at.strftime('%m/%d/%Y'))
    else:
        st.info("No files uploaded yet. Click 'Upload Files' to get started!")

except Exception as e:
    st.error(f"Database connection error: {str(e)}")
    st.info("Make sure the Django backend is properly configured.")
