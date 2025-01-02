import pytest
from wallet.app import Transaction, parse_transactions

@pytest.fixture
def sample_leroy_wiki_data():
    return """
November 5

Transfer, withdraw
 Revolut LT603250052551241431-PLN
Leroy Merlin Wroclaw Ul
Leroy Merlin Wrocla
-PLN 65.97
November 4

Charity, gifts
 Revolut LT603250052551241431-PLN
Paypal *wikipedia
Paypal *wikipedia
-PLN 7.63
"""

class TestTransactionParser:
    def test_leroy_and_wiki_transactions(self, sample_leroy_wiki_data):
        """
        Test parsing of transactions with:
        - Different dates
        - Different categories
        - Different merchants
        - Merchant name variations
        """
        transactions = parse_transactions(sample_leroy_wiki_data)

        # Verify number of transactions
        assert len(transactions) == 2

        # Verify first transaction (Leroy Merlin)
        leroy_transaction = transactions[0]
        assert leroy_transaction.date == "November 5"
        assert leroy_transaction.category == "Transfer, withdraw"
        assert "Revolut" in leroy_transaction.method
        assert leroy_transaction.merchant == "Leroy Merlin Wroclaw Ul"
        assert leroy_transaction.amount == "-PLN 65.97"

        # Verify second transaction (Wikipedia)
        wiki_transaction = transactions[1]
        assert wiki_transaction.date == "November 4"
        assert wiki_transaction.category == "Charity, gifts"
        assert "Revolut" in wiki_transaction.method
        assert wiki_transaction.merchant == "Paypal *wikipedia"
        assert wiki_transaction.amount == "-PLN 7.63"

    def test_amount_formatting(self, sample_leroy_wiki_data):
        """Test that amounts are properly formatted with correct currency and decimals"""
        transactions = parse_transactions(sample_leroy_wiki_data)

        for transaction in transactions:
            # Check amount format (starts with - and ends with two decimal places)
            assert transaction.amount.startswith("-PLN")
            assert len(transaction.amount.split(".")[-1]) == 2

    def test_date_ordering(self, sample_leroy_wiki_data):
        """Test that transactions are ordered by date (newer first)"""
        transactions = parse_transactions(sample_leroy_wiki_data)

        dates = [transaction.date for transaction in transactions]
        assert dates == ["November 5", "November 4"]

    def test_merchant_names(self, sample_leroy_wiki_data):
        """Test handling of merchant names with spaces and special characters"""
        transactions = parse_transactions(sample_leroy_wiki_data)

        merchants = [t.merchant for t in transactions]
        assert "Leroy Merlin Wroclaw Ul" in merchants
        assert "Paypal *wikipedia" in merchants

    def test_categories_preserved(self, sample_leroy_wiki_data):
        """Test that categories are correctly preserved with exact spacing and punctuation"""
        transactions = parse_transactions(sample_leroy_wiki_data)

        categories = [t.category for t in transactions]
        assert "Transfer, withdraw" in categories
        assert "Charity, gifts" in categories

    def test_data_consistency(self, sample_leroy_wiki_data):
        """Test that all fields are present and non-empty for all transactions"""
        transactions = parse_transactions(sample_leroy_wiki_data)

        for transaction in transactions:
            assert all([
                transaction.date,
                transaction.category,
                transaction.method,
                transaction.merchant,
                transaction.amount
            ])

    @pytest.mark.parametrize("expected_field,expected_value", [
        ("date", ["November 5", "November 4"]),
        ("category", ["Transfer, withdraw", "Charity, gifts"]),
        ("merchant", ["Leroy Merlin Wroclaw Ul", "Paypal *wikipedia"]),
        ("amount", ["-PLN 65.97", "-PLN 7.63"])
    ])
    def test_field_values(self, sample_leroy_wiki_data, expected_field, expected_value):
        """Parameterized test for checking specific field values"""
        transactions = parse_transactions(sample_leroy_wiki_data)
        actual_values = [getattr(t, expected_field) for t in transactions]
        assert actual_values == expected_value

    def test_revolut_method_consistency(self, sample_leroy_wiki_data):
        """Test that all transactions have the correct Revolut method string"""
        transactions = parse_transactions(sample_leroy_wiki_data)

        expected_method = "Revolut LT603250052551241431-PLN"
        for transaction in transactions:
            assert transaction.method.strip() == expected_method

    def test_negative_amounts(self, sample_leroy_wiki_data):
        """Test that all amounts are negative (expenses)"""
        transactions = parse_transactions(sample_leroy_wiki_data)

        for transaction in transactions:
            assert transaction.amount.startswith("-PLN")
            # Convert amount to number for comparison
            amount_value = float(transaction.amount.replace("-PLN ", "").replace(",", ""))
            assert amount_value > 0  # Original amount should be positive after removing minus sign



@pytest.fixture
def sample_october_data():
    return """
October 17

Holiday, trips, hotels
 Revolut LT603250052551241431-PLN
Paypal *soundiiz Sound
Paypal *soundiiz Soundiiz
-PLN 19.48
October 16

Health care, doctor
 Revolut LT603250052551241431-PLN
Apteka Medicover
Apteka Medicover
-PLN 34.92

Holiday, trips, hotels
 Revolut LT603250052551241431-PLN
Element 4
Element 4
-PLN 12.00

Income
 Revolut LT603250052551241431-PLN
Refund from Google Payment Ie Ltd
PLN 0.10
"""

class TestTransactionParser:
    def test_multiple_day_transactions(self, sample_october_data):
        """Test parsing of multiple transactions across different days"""
        transactions = parse_transactions(sample_october_data)

        # Verify total number of transactions
        assert len(transactions) == 4

        # Verify October 17 transaction
        oct_17_trans = transactions[0]
        assert oct_17_trans.date == "October 17"
        assert oct_17_trans.category == "Holiday, trips, hotels"
        assert oct_17_trans.merchant == "Paypal *soundiiz Sound"
        assert oct_17_trans.amount == "-PLN 19.48"

        # Verify October 16 transactions (in order)
        assert transactions[1].date == "October 16"
        assert transactions[1].category == "Health care, doctor"
        assert transactions[1].merchant == "Apteka Medicover"
        assert transactions[1].amount == "-PLN 34.92"

        assert transactions[2].date == "October 16"
        assert transactions[2].category == "Holiday, trips, hotels"
        assert transactions[2].merchant == "Element 4"
        assert transactions[2].amount == "-PLN 12.00"

        assert transactions[3].date == "October 16"
        assert transactions[3].category == "Income"
        assert transactions[3].merchant == "Refund from Google Payment Ie Ltd"
        assert transactions[3].amount == "PLN 0.10"

    def test_transaction_types(self, sample_october_data):
        """Test different transaction types (expenses vs income)"""
        transactions = parse_transactions(sample_october_data)

        # Identify expenses and income
        expenses = [t for t in transactions if t.amount.startswith("-")]
        income = [t for t in transactions if not t.amount.startswith("-")]

        assert len(expenses) == 3  # Three expense transactions
        assert len(income) == 1    # One income transaction

        # Verify income transaction
        income_transaction = income[0]
        assert income_transaction.category == "Income"
        assert income_transaction.amount == "PLN 0.10"

    def test_same_day_transactions(self, sample_october_data):
        """Test multiple transactions on the same day"""
        transactions = parse_transactions(sample_october_data)

        oct_16_transactions = [t for t in transactions if t.date == "October 16"]
        assert len(oct_16_transactions) == 3

        # Verify categories for October 16
        categories = [t.category for t in oct_16_transactions]
        assert "Health care, doctor" in categories
        assert "Holiday, trips, hotels" in categories
        assert "Income" in categories

    def test_merchant_names_with_special_chars(self, sample_october_data):
        """Test handling of merchant names with special characters and spaces"""
        transactions = parse_transactions(sample_october_data)

        merchants = [t.merchant for t in transactions]
        assert "Paypal *soundiiz Sound" in merchants
        assert "Refund from Google Payment Ie Ltd" in merchants

    def test_amount_formats(self, sample_october_data):
        """Test various amount formats including small amounts"""
        transactions = parse_transactions(sample_october_data)

        amounts = [t.amount for t in transactions]
        assert "-PLN 19.48" in amounts
        assert "-PLN 34.92" in amounts
        assert "-PLN 12.00" in amounts
        assert "PLN 0.10" in amounts  # Small amount with leading zero

    @pytest.mark.parametrize("expected_date,expected_count", [
        ("October 17", 1),
        ("October 16", 3)
    ])
    def test_transactions_per_date(self, sample_october_data, expected_date, expected_count):
        """Test number of transactions per date"""
        transactions = parse_transactions(sample_october_data)
        date_transactions = [t for t in transactions if t.date == expected_date]
        assert len(date_transactions) == expected_count

    def test_category_counts(self, sample_october_data):
        """Test frequency of categories"""
        transactions = parse_transactions(sample_october_data)

        categories = [t.category for t in transactions]
        category_counts = {
            "Holiday, trips, hotels": categories.count("Holiday, trips, hotels"),
            "Health care, doctor": categories.count("Health care, doctor"),
            "Income": categories.count("Income")
        }

        assert category_counts["Holiday, trips, hotels"] == 2
        assert category_counts["Health care, doctor"] == 1
        assert category_counts["Income"] == 1

    def test_transaction_order(self, sample_october_data):
        """Test that transactions are ordered correctly (by date and sequence)"""
        transactions = parse_transactions(sample_october_data)

        # Verify date ordering
        dates = [t.date for t in transactions]
        assert dates[0] == "October 17"  # Most recent first
        assert all(d == "October 16" for d in dates[1:])  # Followed by October 16 transactions

        # Verify sequence of October 16 transactions
        oct_16_transactions = transactions[1:]
        assert oct_16_transactions[0].category == "Health care, doctor"
        assert oct_16_transactions[1].category == "Holiday, trips, hotels"
        assert oct_16_transactions[2].category == "Income"

    def test_small_amount_handling(self, sample_october_data):
        """Test handling of small amounts (less than 1)"""
        transactions = parse_transactions(sample_october_data)

        small_amount_transaction = [t for t in transactions if t.amount == "PLN 0.10"][0]
        assert small_amount_transaction.category == "Income"
        assert small_amount_transaction.merchant == "Refund from Google Payment Ie Ltd"

    def print_debug_info(self, transactions):
        """Helper method for debugging"""
        for i, t in enumerate(transactions, 1):
            print(f"\nTransaction {i}:")
            print(f"  Date: '{t.date}'")
            print(f"  Category: '{t.category}'")
            print(f"  Method: '{t.method}'")
            print(f"  Merchant: '{t.merchant}'")
            print(f"  Amount: '{t.amount}'")
