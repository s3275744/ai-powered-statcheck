import streamlit as st
from pipeline import StatcheckTester

st.set_page_config(page_title="AI-Powered Statcheck", layout="wide")
st.title("AI-Powered Statcheck Web Interface")

st.write("""
Upload a document (.txt, .pdf, .html, .htm) to automatically extract and check reported NHST tests for consistency.
""")

uploaded_file = st.file_uploader(
    "Choose a file to check (txt, pdf, html, htm)",
    type=["txt", "pdf", "html", "htm"]
)

if uploaded_file is not None:
    # Save uploaded file to a temporary location
    import os
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.name.split(".")[-1]) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    st.info(f"Processing file: {uploaded_file.name}")
    tester = StatcheckTester()
    try:
        context_segments = tester.read_context_from_file(tmp_path)
        if not context_segments:
            st.error("Could not read or parse the file. Please check the file format.")
        else:
            with st.spinner("Extracting and checking statistical tests..."):
                df = tester.perform_statcheck_test(context_segments)
            if df is not None and not df.empty:
                st.success("Statcheck results:")
                st.dataframe(df.style.format(precision=5), use_container_width=True)
            else:
                st.warning("No statistical tests were found or extracted from the document.")
    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        os.remove(tmp_path)
else:
    st.info("Please upload a file to begin.")