import streamlit as st
from apps import json_format
from apps.chat_converter import app as chat_converter

PAGES = {
    "App 1": json_format,
    "Chat Converter": chat_converter
}

def main():
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(PAGES.keys()))

    page = PAGES[selection]

    with st.spinner(f"Loading {selection} ..."):
        page.main()

if __name__ == "__main__":
    main()
