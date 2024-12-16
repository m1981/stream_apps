import streamlit as st
import pandas as pd
from io import StringIO
import tempfile

# Import our previous classes (TransactionParser and TransactionExporter)
# Assuming they are in files transaction_parser.py and transaction_exporter.py
from .parser import TransactionParser
from .formatter import TransactionExporter

def main():
    st.title("Transaction Format Converter")
    st.write("Convert Revolut transactions to CSV format")

    # File upload
    uploaded_file = st.file_uploader("Upload your Revolut transaction file (csv)", type="csv")
    
    if uploaded_file is not None:
        try:
            # Read the uploaded file
            input_text = uploaded_file.getvalue().decode('utf-8')
            
            # Parse transactions
            parser = TransactionParser()
            transactions = parser.parse(input_text)
            
            # Convert to CSV
            exporter = TransactionExporter()
            csv_content = exporter.export_to_csv(transactions)
            
            # Create download button
            st.download_button(
                label="Download converted CSV",
                data=csv_content,
                file_name="converted_transactions.csv",
                mime="text/csv"
            )
            
            # Show preview
            st.subheader("Preview of converted data:")
            preview_df = pd.read_csv(StringIO(csv_content))
            st.dataframe(preview_df)
            
            # Show statistics
            st.subheader("Transaction Statistics:")
            total_inflow = preview_df['Inflow'].sum()
            total_outflow = preview_df['Outflow'].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Income", f"PLN {total_inflow:.2f}")
            with col2:
                st.metric("Total Expenses", f"PLN {total_outflow:.2f}")
            
            st.metric("Net Flow", f"PLN {(total_inflow - total_outflow):.2f}")
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
