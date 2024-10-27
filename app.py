import streamlit as st
from apps import json_format, app2

PAGES = {
    "App 1": json_format,
    "App 2": app2
}

def main():
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(PAGES.keys()))

    page = PAGES[selection]

    with st.spinner(f"Loading {selection} ..."):
        page.main()

if __name__ == "__main__":
    main()
