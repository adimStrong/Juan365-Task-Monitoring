"""
File Browser Page
Search, filter, and manage uploaded files
"""
import streamlit as st
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_all_files, delete_file_asset, get_file_stats
from utils.file_handler import format_file_size

st.set_page_config(
    page_title="Browse Files - Juan365",
    page_icon="\U0001F50D",
    layout="wide"
)

st.title("\U0001F50D Browse Files")
st.markdown("Search, filter, and manage your uploaded files.")

# Filters
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    search_query = st.text_input(
        "Search",
        placeholder="Search by filename...",
        label_visibility="collapsed"
    )

with col2:
    file_type_filter = st.selectbox(
        "File Type",
        options=["all", "image", "video", "document", "other"],
        format_func=lambda x: x.title() if x != "all" else "All Types"
    )

with col3:
    sort_by = st.selectbox(
        "Sort By",
        options=["newest", "oldest", "name", "size"],
        format_func=lambda x: {
            "newest": "Newest First",
            "oldest": "Oldest First",
            "name": "Name A-Z",
            "size": "Size"
        }.get(x, x)
    )

st.markdown("---")

# Get files
try:
    files = list(get_all_files(
        file_type=file_type_filter if file_type_filter != "all" else None,
        search=search_query if search_query else None,
        limit=100
    ))

    # Apply sorting
    if sort_by == "oldest":
        files = sorted(files, key=lambda x: x.created_at)
    elif sort_by == "name":
        files = sorted(files, key=lambda x: x.name.lower())
    elif sort_by == "size":
        files = sorted(files, key=lambda x: x.file_size, reverse=True)
    # newest is default from DB

    # Display results
    st.caption(f"Showing {len(files)} file(s)")

    if files:
        # Table header
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
        with col1:
            st.markdown("**Name**")
        with col2:
            st.markdown("**Type**")
        with col3:
            st.markdown("**Size**")
        with col4:
            st.markdown("**Date**")
        with col5:
            st.markdown("**Actions**")

        st.markdown("---")

        # File rows
        for file in files:
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])

            with col1:
                icon = {
                    'image': '\U0001F5BC',
                    'video': '\U0001F3AC',
                    'document': '\U0001F4C4',
                    'other': '\U0001F4C1'
                }.get(file.file_type, '\U0001F4C1')
                st.write(f"{icon} {file.name}")
                if file.description:
                    st.caption(file.description[:50] + "..." if len(file.description) > 50 else file.description)

            with col2:
                type_colors = {
                    'image': '\U0001F7E2',
                    'video': '\U0001F535',
                    'document': '\U0001F7E1',
                    'other': '\U000026AA'
                }
                st.write(f"{type_colors.get(file.file_type, '')} {file.file_type.title()}")

            with col3:
                st.write(file.file_size_display)

            with col4:
                st.write(file.created_at.strftime('%m/%d/%Y'))

            with col5:
                # View button
                if file.file_type == 'image':
                    if st.button("\U0001F441", key=f"view_{file.id}", help="View"):
                        st.session_state[f'show_image_{file.id}'] = True

                # Delete button
                if st.button("\U0001F5D1", key=f"delete_{file.id}", help="Delete"):
                    st.session_state[f'confirm_delete_{file.id}'] = True

            # Image preview modal
            if st.session_state.get(f'show_image_{file.id}'):
                with st.expander(f"Preview: {file.name}", expanded=True):
                    try:
                        from config import MEDIA_ROOT
                        file_path = MEDIA_ROOT / file.file.name
                        if file_path.exists():
                            st.image(str(file_path), use_container_width=True)
                        else:
                            st.error("File not found on disk")
                    except Exception as e:
                        st.error(f"Could not load image: {e}")

                    if st.button("Close", key=f"close_{file.id}"):
                        del st.session_state[f'show_image_{file.id}']
                        st.rerun()

            # Delete confirmation
            if st.session_state.get(f'confirm_delete_{file.id}'):
                with st.container():
                    st.warning(f"Are you sure you want to delete '{file.name}'?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes, Delete", key=f"confirm_yes_{file.id}", type="primary"):
                            if delete_file_asset(file.id):
                                st.success("File deleted!")
                                del st.session_state[f'confirm_delete_{file.id}']
                                st.rerun()
                            else:
                                st.error("Failed to delete file")
                    with col_no:
                        if st.button("Cancel", key=f"confirm_no_{file.id}"):
                            del st.session_state[f'confirm_delete_{file.id}']
                            st.rerun()

            st.markdown("---")

    else:
        st.info("\U0001F4C2 No files found. Upload some files to get started!")
        if st.button("\U0001F4E4 Go to Upload"):
            st.switch_page("pages/1_Upload.py")

except Exception as e:
    st.error(f"Error loading files: {str(e)}")
    st.info("Make sure the database is properly configured.")
