import os
import streamlit as st
from todoist_api_python.api import TodoistAPI


def get_project_descriptions(api, projects):
    project_descriptions = {}
    for project in projects:
        tasks = api.get_tasks(project_id=project.id)

        description_found = False
        for task in tasks:
            if task.content == "Description":
                if task.description:
                    project_descriptions[project.id] = task.description
                    description_found = True
                    break

        if not description_found:
            project_descriptions[project.id] = "-----------------"

    return project_descriptions

def organize_projects_and_sections(projects):
    # Create a list to hold ordered projects and sections
    organized_items = []
    project_map = {project.id: project for project in projects}

    # Recursive function to display projects and their sections correctly
    def add_items(parent_id, depth):
        for project in sorted(projects, key=lambda x: x.name):
            if project.parent_id == parent_id:
                project.depth = depth
                organized_items.append(project)
                # Recursively add child projects
                add_items(project.id, depth + 2)

    add_items(None, 0)  # Start with top-level projects
    return organized_items

def main():
    # Title and description
    st.title("📋 Todoist Projects Overview")

    # Add some custom CSS to make it look better
    st.markdown("""
        <style>
        .project-item {
            padding: 5px;
            border-radius: 5px;
            margin: 2px 0;
        }
        .project-description {
            color: #666;
            font-style: italic;
        }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("*A hierarchical view of your Todoist projects with descriptions*")

    # Sidebar for API key input
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input(
            "Todoist API Key",
            value=os.environ.get('TODOIST_KEY', ''),
            type="password"
        )
        st.markdown("*Get your API key from [Todoist Settings](https://todoist.com/app/settings/integrations)*")

    if not api_key:
        st.warning("Please enter your Todoist API key in the sidebar")
        return

    try:
        # Initialize API and get data
        api = TodoistAPI(api_key)

        with st.spinner("Loading projects..."):
            projects = api.get_projects()
            project_descriptions = get_project_descriptions(api, projects)
            organized_items = organize_projects_and_sections(projects)

        # Display projects in an expandable container
        with st.expander("All Projects", expanded=True):
            for item in organized_items:
                # Calculate indentation
                indent = "    " * item.depth

                # Create a container for each project
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.markdown(f"""
                        **{item.name}**
                        """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                            {project_descriptions[item.id]}
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please check your API key and try again")

if __name__ == '__main__':
    main()
