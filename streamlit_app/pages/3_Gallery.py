"""
Gallery View Page
Visual gallery for images and videos
"""
import streamlit as st
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_all_files
from config import MEDIA_ROOT

st.set_page_config(
    page_title="Gallery - Juan365",
    page_icon="\U0001F5BC",
    layout="wide"
)

st.title("\U0001F5BC Gallery")
st.markdown("Browse your images and videos in a visual grid.")

# Tabs for Images and Videos
tab1, tab2 = st.tabs(["\U0001F5BC Images", "\U0001F3AC Videos"])

with tab1:
    st.subheader("Images")

    try:
        images = list(get_all_files(file_type='image', limit=50))

        if images:
            # Grid layout - 4 columns
            cols = st.columns(4)

            for i, image in enumerate(images):
                with cols[i % 4]:
                    try:
                        file_path = MEDIA_ROOT / image.file.name
                        if file_path.exists():
                            st.image(str(file_path), use_container_width=True)
                            st.caption(f"{image.name[:30]}...")
                            st.caption(f"\U0001F4C5 {image.created_at.strftime('%m/%d/%Y')}")
                        else:
                            st.warning(f"File not found: {image.name}")
                    except Exception as e:
                        st.error(f"Error: {image.name}")

        else:
            st.info("\U0001F5BC No images uploaded yet.")
            if st.button("\U0001F4E4 Upload Images"):
                st.switch_page("pages/1_Upload.py")

    except Exception as e:
        st.error(f"Error loading images: {str(e)}")

with tab2:
    st.subheader("Videos")

    try:
        videos = list(get_all_files(file_type='video', limit=20))

        if videos:
            for video in videos:
                col1, col2 = st.columns([3, 1])

                with col1:
                    try:
                        file_path = MEDIA_ROOT / video.file.name
                        if file_path.exists():
                            st.video(str(file_path))
                        else:
                            st.warning(f"Video file not found: {video.name}")
                    except Exception as e:
                        st.error(f"Cannot play video: {video.name}")

                with col2:
                    st.markdown(f"**{video.name}**")
                    st.caption(f"Size: {video.file_size_display}")
                    st.caption(f"Uploaded: {video.created_at.strftime('%m/%d/%Y')}")
                    if video.description:
                        st.caption(video.description[:100])

                st.markdown("---")

        else:
            st.info("\U0001F3AC No videos uploaded yet.")
            if st.button("\U0001F4E4 Upload Videos"):
                st.switch_page("pages/1_Upload.py")

    except Exception as e:
        st.error(f"Error loading videos: {str(e)}")

# Sidebar stats
with st.sidebar:
    st.markdown("### Gallery Stats")
    try:
        from utils.db import get_file_stats
        stats = get_file_stats()
        st.metric("\U0001F5BC Images", stats.get('image_count', 0))
        st.metric("\U0001F3AC Videos", stats.get('video_count', 0))
    except Exception:
        pass
