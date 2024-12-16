import streamlit as st
import io
import os
from .converter import AliorNewRorConverter, AliorNewCardConverter

def main():
    st.title("Alior Bank CSV Converter for YNAB")
    st.write("Upload your Alior Bank CSV files to convert them to YNAB format.")

    # File uploader for regular account
    st.subheader("Regular Account Statement")
    regular_file = st.file_uploader("Choose Alior regular account CSV file", type="csv", key="regular")

    # File uploader for card account
    st.subheader("Card Statement")
    card_file = st.file_uploader("Choose Alior card CSV file", type="csv", key="card")

    if st.button("Convert Files"):
        converted_files = []

        # Process regular account file
        if regular_file is not None:
            try:
                # Create converter instance
                converter = AliorNewRorConverter()
                
                # Save uploaded file temporarily with correct encoding
                with io.BytesIO(regular_file.getvalue()) as temp_file:
                    content = temp_file.read().decode('windows-1250')  # Changed from utf-8 to windows-1250
                    temp_path = "temp_regular.csv"
                    with open(temp_path, 'w', encoding='windows-1250') as f:  # Changed encoding here too
                        f.write(content)
                
                # Convert file
                converter.load(temp_path)
                converter.convertToYnab(start_from_row=2)
                converted_content = converter.getStr()
                
                # Create downloadable file
                converted_file = io.BytesIO()
                converted_file.write(converted_content.encode('utf-8'))  # Keep UTF-8 for output
                converted_file.seek(0)
                
                # Add download button
                st.download_button(
                    label="Download converted regular account CSV",
                    data=converted_file,
                    file_name="YNAB_alior.csv",
                    mime="text/csv",
                    key="download_regular"
                )
                
                # Cleanup
                os.remove(temp_path)
                st.success("Regular account file converted successfully!")
                
            except Exception as e:
                st.error(f"Error processing regular account file: {str(e)}")

        # Process card file
        if card_file is not None:
            try:
                # Create converter instance
                converter = AliorNewCardConverter()
                
                # Save uploaded file temporarily with correct encoding
                with io.BytesIO(card_file.getvalue()) as temp_file:
                    content = temp_file.read().decode('windows-1250')  # Changed from utf-8 to windows-1250
                    temp_path = "temp_card.csv"
                    with open(temp_path, 'w', encoding='windows-1250') as f:  # Changed encoding here too
                        f.write(content)
                
                # Convert file
                converter.load(temp_path)
                converter.convertToYnab(start_from_row=2)
                converted_content = converter.getStr()
                
                # Create downloadable file
                converted_file = io.BytesIO()
                converted_file.write(converted_content.encode('utf-8'))  # Keep UTF-8 for output
                converted_file.seek(0)
                
                # Add download button
                st.download_button(
                    label="Download converted card CSV",
                    data=converted_file,
                    file_name="YNAB_alior_card.csv",
                    mime="text/csv",
                    key="download_card"
                )
                
                # Cleanup
                os.remove(temp_path)
                st.success("Card file converted successfully!")
                
            except Exception as e:
                st.error(f"Error processing card file: {str(e)}")

if __name__ == "__main__":
    main()
