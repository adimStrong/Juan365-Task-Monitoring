"""
Documents Viewer Page
View and manage document files
"""
import streamlit as st
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_all_files, delete_file_asset
from config import MEDIA_ROOT

st.set_page_config(
    page_title="Documents - Juan365",
    page_icon="\U0001F4C4",
    layout="wide"
)

st.title("\U0001F4C4 Documents")
st.markdown("View and manage your uploaded documents.")

# Search
search = st.text_input("Search documents...", placeholder="Enter filename...")

try:
    documents = list(get_all_files(
        file_type='document',
        search=search if search else None,
        limit=50
    ))

    if documents:
        st.caption(f"Found {len(documents)} document(s)")
        st.markdown("---")

        for doc in documents:
            with st.container():
                col1, col2, col3 = st.columns([4, 1, 1])

                with col1:
                    # Document icon based on extension
                    ext = doc.name.split('.')[-1].lower() if '.' in doc.name else ''
                    icons = {
                        'pdf': '\U0001F4D5',
                        'doc': '\U0001F4DD',
                        'docx': '\U0001F4DD',
                        'xls': '\U0001F4CA',
                        'xlsx': '\U0001F4CA',
                        'ppt': '\U0001F4CA',
                        'pptx': '\U0001F4CA',
                        'txt': '\U0001F4C3',
                        'csv': '\U0001F4C3',
                    }
                    icon = icons.get(ext, '\U0001F4C4')

                    st.markdown(f"### {icon} {doc.name}")

                    if doc.description:
                        st.write(doc.description)

                    if doc.tags:
                        tags_list = [t.strip() for t in doc.tags.split(',') if t.strip()]
                        st.write(" ".join([f"`{tag}`" for tag in tags_list]))

                with col2:
                    st.caption("**Size**")
                    st.write(doc.file_size_display)
                    st.caption("**Uploaded**")
                    st.write(doc.created_at.strftime('%m/%d/%Y'))

                with col3:
                    # Download button
                    try:
                        file_path = MEDIA_ROOT / doc.file.name
                        if file_path.exists():
                            with open(file_path, 'rb') as f:
                                st.download_button(
                                    label="\U0001F4E5 Download",
                                    data=f.read(),
                                    file_name=doc.name,
                                    mime=doc.mime_type or 'application/octet-stream',
                                    key=f"download_{doc.id}"
                                )
                        else:
                            st.warning("File missing")
                    except Exception as e:
                        st.error("Download error")

                    # Delete button
                    if st.button("\U0001F5D1 Delete", key=f"del_{doc.id}"):
                        st.session_state[f'confirm_del_{doc.id}'] = True

                # Delete confirmation
                if st.session_state.get(f'confirm_del_{doc.id}'):
                    st.warning(f"Delete '{doc.name}'?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Yes", key=f"yes_{doc.id}"):
                            delete_file_asset(doc.id)
                            st.success("Deleted!")
                            del st.session_state[f'confirm_del_{doc.id}']
                            st.rerun()
                    with c2:
                        if st.button("No", key=f"no_{doc.id}"):
                            del st.session_state[f'confirm_del_{doc.id}']
                            st.rerun()

                # PDF Preview
                if ext == 'pdf':
                    with st.expander("\U0001F4D6 Preview PDF"):
                        try:
                            file_path = MEDIA_ROOT / doc.file.name
                            if file_path.exists():
                                # Display PDF info
                                st.info(f"PDF file: {doc.file_size_display}")
                                st.caption("Use the download button to view the full PDF.")
                            else:
                                st.warning("PDF file not found on disk")
                        except Exception as e:
                            st.error(f"Cannot preview: {e}")

                st.markdown("---")

    else:
        st.info("\U0001F4C4 No documents uploaded yet.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("\U0001F4E4 Upload Documents", use_container_width=True):
                st.switch_page("pages/1_Upload.py")
        with col2:
            if st.button("\U0001F50D Browse All Files", use_container_width=True):
                st.switch_page("pages/2_Browse.py")

except Exception as e:
    st.error(f"Error loading documents: {str(e)}")
    st.info("Check database configuration.")

# Sidebar - document types
with st.sidebar:
    st.markdown("### Document Types")
    st.markdown("""
    **Supported formats:**
    - \U0001F4D5 PDF
    - \U0001F4DD Word (.doc, .docx)
    - \U0001F4CA Excel (.xls, .xlsx)
    - \U0001F4CA PowerPoint (.ppt, .pptx)
    - \U0001F4C3 Text (.txt, .csv)
    """)
