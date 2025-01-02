import pytest
from datetime import datetime
from typing import List
import pandas as pd
import numpy as np
from wallet.app import (  # assuming this is your main file
    Transaction,
    parse_transactions,
    convert_to_dataframe
)

# Fixtures
@pytest.fixture
def sample_transaction_data() -> str:
    """Provides a basic valid transaction data sample."""
    return """
September 28

Holiday, trips, hotels
 Revolut LT603250052551241431-PLN
Delikatesy Konkret
Delikatesy Konkret
-PLN 57.00
"""

@pytest.fixture
def multiple_transactions_data() -> str:
    """Provides multiple transactions for testing."""
    return """
September 28

Holiday, trips, hotels
 Revolut LT603250052551241431-PLN
Delikatesy Konkret
Delikatesy Konkret
-PLN 57.00

Income
 Revolut LT603250052551241431-PLN
Top-Up by *5193
PLN 1,000.00
"""

@pytest.fixture
def edge_case_data() -> str:
    """Provides edge cases in transaction data."""
    return """
September 28

Holiday, trips, hotels
 Revolut LT603250052551241431-PLN
Merchant with, comma
Merchant with, comma
-PLN 1,234.56

Income
 Revolut LT603250052551241431-PLN
Merchant with
multiple lines
PLN 1.00
"""

class TestTransactionParser:
    """Test suite for transaction parsing functionality."""

    def test_basic_transaction_parsing(self, sample_transaction_data):
        """Test parsing of a single, well-formed transaction."""
        transactions = parse_transactions(sample_transaction_data)

        assert len(transactions) == 1
        transaction = transactions[0]
        assert transaction.date == "September 28"
        assert transaction.category == "Holiday, trips, hotels"
        assert "Revolut" in transaction.method
        assert transaction.merchant == "Delikatesy Konkret"
        assert transaction.amount == "-PLN 57.00"

    def test_multiple_transactions(self, multiple_transactions_data):
        """Test parsing of multiple transactions."""
        transactions = parse_transactions(multiple_transactions_data)

        # Debug print for troubleshooting
        for i, t in enumerate(transactions):
            print(f"Transaction {i}:")
            print(f"  Date: {t.date}")
            print(f"  Category: {t.category}")
            print(f"  Method: {t.method}")
            print(f"  Merchant: {t.merchant}")
            print(f"  Amount: {t.amount}")
            print()

        assert len(transactions) == 2
        # Verify first transaction
        assert transactions[0].category == "Holiday, trips, hotels"
        assert transactions[0].amount == "-PLN 57.00"
        assert transactions[0].merchant == "Delikatesy Konkret"

        # Verify second transaction
        assert transactions[1].category == "Income"
        assert transactions[1].amount == "PLN 1,000.00"
        assert transactions[1].merchant == "Top-Up by *5193"


    @pytest.mark.parametrize("input_data,expected_count", [
        ("", 0),  # Empty input
        ("\n\n", 0),  # Only newlines
        ("September 28\n\n", 0),  # Only date
    ])
    def test_empty_and_partial_inputs(self, input_data, expected_count):
        """Test handling of empty and partial inputs."""
        transactions = parse_transactions(input_data)
        assert len(transactions) == expected_count

    def test_malformed_data_handling(self):
        """Test handling of malformed transaction data."""
        malformed_data = """
        September 28
        Invalid Category
        Some random text
        -PLN 50.00
        """
        transactions = parse_transactions(malformed_data)
        assert len(transactions) == 0  # Should not parse invalid transactions

    def test_date_parsing(self):
        """Test various date formats and validations."""
        data_with_various_dates = """
        September 28

        Category
         Revolut LT603250052551241431-PLN
        Merchant
        Merchant
        -PLN 57.00

        October 1

        Category
         Revolut LT603250052551241431-PLN
        Merchant
        Merchant
        -PLN 58.00
        """
        transactions = parse_transactions(data_with_various_dates)
        assert transactions[0].date == "September 28"
        assert transactions[1].date == "October 1"

    def test_amount_parsing(self):
        """Test various amount formats."""
        amounts_data = """
        September 28

        Category
         Revolut LT603250052551241431-PLN
        Merchant
        Merchant
        -PLN 1,234.56

        Category
         Revolut LT603250052551241431-PLN
        Merchant
        Merchant
        PLN 1.00
        """
        transactions = parse_transactions(amounts_data)
        assert transactions[0].amount == "-PLN 1,234.56"
        assert transactions[1].amount == "PLN 1.00"

class TestDataFrameConversion:
    """Test suite for DataFrame conversion functionality."""

    def test_basic_conversion(self, sample_transaction_data):
        """Test basic conversion to DataFrame."""
        transactions = parse_transactions(sample_transaction_data)
        df = convert_to_dataframe(transactions)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert all(col in df.columns for col in ['Date', 'Category', 'Method', 'Merchant', 'Amount'])

    def test_empty_conversion(self):
        """Test conversion of empty transaction list."""
        df = convert_to_dataframe([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert all(col in df.columns for col in ['Date', 'Category', 'Method', 'Merchant', 'Amount'])

    def test_dataframe_dtypes(self, multiple_transactions_data):
        """Test DataFrame column types."""
        transactions = parse_transactions(multiple_transactions_data)
        df = convert_to_dataframe(transactions)

        assert df['Date'].dtype == object
        assert df['Amount'].dtype == object
        assert df['Category'].dtype == object

    @pytest.mark.parametrize("field,expected_type", [
        ('date', str),
        ('category', str),
        ('method', str),
        ('merchant', str),
        ('amount', str)
    ])
    def test_transaction_field_types(self, sample_transaction_data, field, expected_type):
        """Test types of individual Transaction fields."""
        transactions = parse_transactions(sample_transaction_data)
        assert isinstance(getattr(transactions[0], field), expected_type)

def test_integration_full_workflow(multiple_transactions_data):
    """Integration test for the full workflow."""
    # Parse transactions
    transactions = parse_transactions(multiple_transactions_data)
    assert len(transactions) > 0

    # Convert to DataFrame
    df = convert_to_dataframe(transactions)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == len(transactions)

    # Verify data integrity
    assert df.iloc[0]['Amount'] == transactions[0].amount
    assert df.iloc[0]['Date'] == transactions[0].date

if __name__ == "__main__":
    pytest.main(["-v"])
