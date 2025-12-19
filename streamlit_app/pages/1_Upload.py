"""
File Upload Page
Upload images, videos, and documents
"""
import streamlit as st
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SUPPORTED_IMAGES, SUPPORTED_VIDEOS, SUPPORTED_DOCUMENTS
from utils.file_handler import (
    get_file_type, get_mime_type, validate_file_size,
    save_uploaded_file, format_file_size, get_max_size_mb
)
from utils.db import create_file_asset, get_all_users, get_all_tickets

st.set_page_config(
    page_title="Upload Files - Juan365",
    page_icon="\U0001F4E4",
    layout="wide"
)

st.title("\U0001F4E4 Upload Files")
st.markdown("Upload images, videos, documents, and other files to your Juan365 storage.")

# File type info
with st.expander("\U0001F4CB Supported File Types & Limits"):
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("**Images**")
        st.caption(f"Max: {get_max_size_mb('image')} MB")
        st.caption(", ".join(SUPPORTED_IMAGES))

    with col2:
        st.markdown("**Videos**")
        st.caption(f"Max: {get_max_size_mb('video')} MB")
        st.caption(", ".join(SUPPORTED_VIDEOS))

    with col3:
        st.markdown("**Documents**")
        st.caption(f"Max: {get_max_size_mb('document')} MB")
        st.caption(", ".join(SUPPORTED_DOCUMENTS))

    with col4:
        st.markdown("**Other**")
        st.caption(f"Max: {get_max_size_mb('other')} MB")
        st.caption("Any file type")

st.markdown("---")

# Upload form
uploaded_files = st.file_uploader(
    "Choose files to upload",
    accept_multiple_files=True,
    help="You can upload multiple files at once"
)

if uploaded_files:
    st.subheader(f"\U0001F4C2 {len(uploaded_files)} file(s) selected")

    # Optional metadata
    with st.expander("\U0001F3F7 Add metadata (optional)", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            description = st.text_area(
                "Description",
                placeholder="Add a description for all uploaded files...",
                height=100
            )

        with col2:
            tags = st.text_input(
                "Tags",
                placeholder="tag1, tag2, tag3",
                help="Comma-separated tags for easier searching"
            )

        # Link to ticket (optional)
        try:
            tickets = list(get_all_tickets())
            if tickets:
                st.markdown("**Link to Ticket (optional)**")

                # Create ticket options with more details
                ticket_options = {"None - No ticket link": None}
                for t in tickets:
                    status_icon = {
                        'requested': '\U0001F7E1',  # yellow
                        'approved': '\U0001F7E2',   # green
                        'in_progress': '\U0001F535', # blue
                        'completed': '\U00002705',   # check
                        'rejected': '\U0001F534'     # red
                    }.get(t.status, '\U000026AA')

                    priority_icon = {
                        'urgent': '\U0001F525',  # fire
                        'high': '\U0001F7E0',    # orange
                        'medium': '\U0001F7E1',  # yellow
                        'low': '\U0001F7E2'      # green
                    }.get(t.priority, '')

                    ticket_label = f"#{t.id} {status_icon} {priority_icon} {t.title[:40]}"
                    ticket_options[ticket_label] = t.id

                selected_ticket = st.selectbox(
                    "Select Ticket",
                    options=list(ticket_options.keys()),
                    label_visibility="collapsed"
                )
                ticket_id = ticket_options.get(selected_ticket)

                # Show selected ticket details
                if ticket_id:
                    selected = next((t for t in tickets if t.id == ticket_id), None)
                    if selected:
                        with st.container():
                            st.markdown("---")
                            st.markdown(f"**Ticket #{selected.id}: {selected.title}**")

                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.caption(f"Status: **{selected.get_status_display()}**")
                            with col_b:
                                st.caption(f"Priority: **{selected.get_priority_display()}**")
                            with col_c:
                                if selected.assigned_to:
                                    st.caption(f"Assigned: **{selected.assigned_to.username}**")
                                else:
                                    st.caption("Assigned: **Unassigned**")

                            if selected.description:
                                st.markdown("**Description:**")
                                st.text(selected.description[:300] + "..." if len(selected.description) > 300 else selected.description)

                            if selected.deadline:
                                st.caption(f"Deadline: {selected.deadline.strftime('%Y-%m-%d %H:%M')}")
            else:
                ticket_id = None
                st.caption("No tickets available")
        except Exception as e:
            ticket_id = None
            st.caption(f"Could not load tickets: {e}")

    # Preview uploaded files
    st.markdown("### Preview")

    valid_files = []
    for i, file in enumerate(uploaded_files):
        file_type = get_file_type(file.name, file.type)
        file_size = file.size
        is_valid = validate_file_size(file_size, file_type)

        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

        with col1:
            icon = {
                'image': '\U0001F5BC',
                'video': '\U0001F3AC',
                'document': '\U0001F4C4',
                'other': '\U0001F4C1'
            }.get(file_type, '\U0001F4C1')
            st.write(f"{icon} **{file.name}**")

        with col2:
            st.caption(file_type.upper())

        with col3:
            st.caption(format_file_size(file_size))

        with col4:
            if is_valid:
                st.write("\U00002705 Ready")
                valid_files.append(file)
            else:
                max_size = get_max_size_mb(file_type)
                st.write(f"\U0000274C Max {max_size}MB")

        # Image preview
        if file_type == 'image' and is_valid:
            try:
                st.image(file, width=200)
            except Exception:
                pass

    st.markdown("---")

    # Upload button
    if valid_files:
        if st.button(f"\U0001F680 Upload {len(valid_files)} file(s)", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()

            success_count = 0
            error_count = 0

            for i, file in enumerate(valid_files):
                status_text.text(f"Uploading: {file.name}...")
                progress = (i + 1) / len(valid_files)
                progress_bar.progress(progress)

                try:
                    # Save file to disk
                    full_path, relative_path = save_uploaded_file(file)

                    # Get file metadata
                    file_type = get_file_type(file.name, file.type)
                    mime_type = file.type or get_mime_type(file.name)

                    # Create database record
                    create_file_asset(
                        name=file.name,
                        file_path=relative_path,
                        file_type=file_type,
                        mime_type=mime_type,
                        file_size=file.size,
                        description=description if 'description' in dir() else '',
                        tags=tags if 'tags' in dir() else '',
                        ticket_id=ticket_id if 'ticket_id' in dir() else None
                    )

                    success_count += 1

                except Exception as e:
                    st.error(f"Error uploading {file.name}: {str(e)}")
                    error_count += 1

            progress_bar.empty()
            status_text.empty()

            if success_count > 0:
                st.success(f"\U0001F389 Successfully uploaded {success_count} file(s)!")

            if error_count > 0:
                st.warning(f"\U0000274C Failed to upload {error_count} file(s)")

            # Clear uploader
            st.balloons()

    else:
        st.warning("No valid files to upload. Check file size limits.")

else:
    # Drop zone placeholder
    st.markdown("""
    <div style="
        border: 2px dashed #CBD5E1;
        border-radius: 1rem;
        padding: 3rem;
        text-align: center;
        color: #94A3B8;
        margin: 2rem 0;
    ">
        <p style="font-size: 3rem; margin-bottom: 1rem;">\U0001F4E4</p>
        <p style="font-size: 1.2rem;">Drag and drop files here</p>
        <p>or click "Browse files" above</p>
    </div>
    """, unsafe_allow_html=True)
