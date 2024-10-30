import streamlit as st
from apps.json_format import app as json_format
from apps.chat_converter import app as chat_converter
from apps.json_merge import app as json_merge
from apps.chat1 import app as chat1
PAGES = {
    "Chat": chat1,
    "Chat Converter": chat_converter,
    "Json formatter": json_format,
    "Json merge": json_merge,
}

def main():
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(PAGES.keys()))

    page = PAGES[selection]

    with st.spinner(f"Loading {selection} ..."):
        page.main()

if __name__ == "__main__":
    main()
