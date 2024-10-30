import streamlit as st
import json
import io

def format_json_file(content):
    try:
        data = json.loads(content)
        return json.dumps(data, indent=4, ensure_ascii=False)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON data: {e}")
        return None

def main():
    st.title("JSON Formatter")
    st.write("Upload a JSON file to format it to a human-readable form and download it.")

    uploaded_file = st.file_uploader("Choose a JSON file", type="json")

    if uploaded_file is not None:
        # Reading and formatting JSON file
        content = uploaded_file.read().decode("utf-8")
        formatted_json = format_json_file(content)

        if formatted_json:
            # st.code(formatted_json, language='json')

            # Create a downloadable file
            download_file = io.BytesIO()
            download_file.write(formatted_json.encode('utf-8'))
            download_file.seek(0)

            st.download_button(
                label="Download formatted JSON",
                data=download_file,
                file_name="formatted.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()
