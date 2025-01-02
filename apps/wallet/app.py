import streamlit as st
import pandas as pd
from io import StringIO
import re
from dataclasses import dataclass
from typing import List
import csv

@dataclass
class Transaction:
    date: str
    category: str
    method: str
    merchant: str
    amount: str

def parse_transactions(data):
    # Split the input data by lines and remove empty lines
    lines = [line.strip() for line in data.strip().split('\n') if line.strip()]

    # Initialize variables
    transactions = []
    current_transaction = None
    current_date = None

    # Regular expressions
    date_pattern = re.compile(r'^[A-Za-z]+\s+\d+$')
    amount_pattern = re.compile(r'([-+]?PLN\s*[\d,\.]+)')
    revolut_pattern = re.compile(r'.*Revolut.*PLN')

    for i, line in enumerate(lines):
        # Check for date
        if date_pattern.match(line):
            current_date = line
            continue

        # Start new transaction when Revolut line is found
        if revolut_pattern.match(line):
            if current_transaction is not None:
                transactions.append(current_transaction)

            # Get the category from the previous line
            # Make sure we don't go out of bounds
            category = lines[i - 1] if i > 0 else None

            current_transaction = Transaction(
                date=current_date,
                category=category,
                method=line,
                merchant=None,
                amount=None
            )

        # Check for amount - this completes a transaction
        elif amount_pattern.search(line) and current_transaction is not None:
            current_transaction.amount = amount_pattern.search(line).group(0)
            transactions.append(current_transaction)
            current_transaction = None

        # If we have a current transaction and no amount pattern, it must be merchant name
        elif current_transaction is not None and not current_transaction.merchant:
            current_transaction.merchant = line

    # Add the last transaction if exists
    if current_transaction is not None and current_transaction.amount is not None:
        transactions.append(current_transaction)

    return transactions


def convert_to_dataframe(transactions):
    data = {
        'Date': [],
        'Category': [],
        'Method': [],
        'Merchant': [],
        'Amount': []
    }
    
    for trans in transactions:
        data['Date'].append(trans.date)
        data['Category'].append(trans.category)
        data['Method'].append(trans.method)
        data['Merchant'].append(trans.merchant)
        data['Amount'].append(trans.amount)
    
    return pd.DataFrame(data)

def main():
    st.title("Transaction Format Converter")
    st.write("Convert Revolut transactions to CSV format")

    # File upload
    uploaded_file = st.file_uploader("Upload your Revolut transaction file", type=["txt", "csv"])
    
    if uploaded_file is not None:
        try:
            # Read the uploaded file
            input_text = uploaded_file.getvalue().decode('utf-8')
            
            # Parse transactions
            transactions = parse_transactions(input_text)
            
            # Convert to DataFrame
            df = convert_to_dataframe(transactions)
            
            # Create CSV content
            csv_content = df.to_csv(index=False)
            
            # Create download button
            st.download_button(
                label="Download converted CSV",
                data=csv_content,
                file_name="converted_transactions.csv",
                mime="text/csv"
            )
            
            # Show preview
            st.subheader("Preview of converted data:")
            st.dataframe(df)

            # Additional statistics
            st.subheader("Transaction Details:")
            st.write(f"Total transactions: {len(transactions)}")
            
            # Show some basic statistics
            if len(transactions) > 0:
                # Convert amounts to numeric values for calculations
                amounts = pd.to_numeric(
                    df['Amount'].str.replace('PLN', '')
                    .str.replace(',', '')
                    .str.strip(), 
                    errors='coerce'
                )
                
                st.write(f"Total amount: PLN {abs(amounts.sum()):.2f}")
                st.write(f"Average transaction amount: PLN {abs(amounts.mean()):.2f}")
                
                # Show transactions by category
                st.subheader("Transactions by Category:")
                category_counts = df['Category'].value_counts()
                st.bar_chart(category_counts)

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
