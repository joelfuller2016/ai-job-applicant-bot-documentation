import streamlit as st


def resume_page():
    st.header("Resume Upload")
    uploaded_file = st.file_uploader("Upload your resume", type=["pdf", "docx", "txt"])
    if uploaded_file:
        st.success(f"Uploaded {uploaded_file.name}")
        # Placeholder for parsing logic
        st.write("Resume parsing is not yet implemented.")


def job_search_page():
    st.header("Job Search")
    title = st.text_input("Job Title")
    location = st.text_input("Location")
    if st.button("Search"):
        # Placeholder for search logic
        st.write(f"Searching jobs for '{title}' in '{location}' ...")
        st.info("Job search functionality is not yet implemented.")


def application_tracker_page():
    st.header("Application Tracker")
    st.write("This page will show applied jobs and statuses.")


def main():
    st.sidebar.title("AI Job Applicant Bot")
    page = st.sidebar.radio(
        "Navigate",
        ("Resume", "Job Search", "Applications"),
    )

    if page == "Resume":
        resume_page()
    elif page == "Job Search":
        job_search_page()
    elif page == "Applications":
        application_tracker_page()


if __name__ == "__main__":
    main()

