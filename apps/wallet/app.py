import streamlit as st
import pandas as pd
from io import StringIO
from decimal import Decimal
from datetime import datetime

from dataclasses import dataclass
from typing import List, Optional
import io

# Assuming we're using the classes we created earlier
from .parser import TransactionParser
from .exporter import TransactionCsvExporter

def main():
    st.title("Transaction Format Converter")
    st.write("Convert Revolut transactions to CSV format")

    # File upload - note we're changing to text file since our parser expects text
    uploaded_file = st.file_uploader("Upload your Revolut transaction file (csv)", type="csv")
    
    if uploaded_file is not None:
        try:
            # Read the uploaded file
            input_text = uploaded_file.getvalue().decode('utf-8')
            
            # Parse transactions using our parser
            parser = TransactionParser()
            daily_transactions = parser.parse(input_text)
            
            # Convert to CSV using our exporter
            output = io.StringIO()
            exporter = TransactionCsvExporter()
            exporter.export_to_csv(daily_transactions, output)
            
            # Get CSV content
            csv_content = output.getvalue()
            
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
            total_inflow = preview_df['Inflow'].fillna(0).sum()
            total_outflow = preview_df['Outflow'].fillna(0).sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Income", f"PLN {total_inflow:.2f}")
            with col2:
                st.metric("Total Expenses", f"PLN {total_outflow:.2f}")
            
            st.metric("Net Flow", f"PLN {(total_inflow - total_outflow):.2f}")

            # Additional statistics from our parsed data
            st.subheader("Transaction Details:")
            total_days = len(daily_transactions)
            total_transactions = sum(len(day.transactions) for day in daily_transactions)
            
            col3, col4 = st.columns(2)
            with col3:
                st.metric("Total Days", total_days)
            with col4:
                st.metric("Total Transactions", total_transactions)
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
