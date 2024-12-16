import pytest
from decimal import Decimal
from datetime import datetime
from typing import List

# Assuming all previous code is in parser.py
from parser2 import (
    TransactionParser, Amount, Account, Transaction, DailyTransactions,
    ParserError, InvalidDateFormatError, InvalidAmountFormatError, InvalidTransactionFormatError
)

class TestAmount:
    def test_valid_positive_amount(self):
        amount = Amount.from_string("PLN 100.00")
        assert amount.value == Decimal("100.00")
        assert amount.currency == "PLN"

    def test_valid_negative_amount(self):
        amount = Amount.from_string("-PLN 50.75")
        assert amount.value == Decimal("-50.75")
        assert amount.currency == "PLN"

    @pytest.mark.parametrize("invalid_input", [
        "PLN100.00",  # No space
        "PLN -100.00",  # Wrong sign position
        "100.00 PLN",  # Wrong order
        "PLN 100.00.00",  # Multiple decimal points
        "PLN abc",  # Non-numeric
        "PLNN 100.00",  # Invalid currency
        "PLN 100,00",  # Wrong decimal separator
        "",  # Empty string
        "PLN ",  # Missing amount
        " 100.00",  # Missing currency
    ])
    def test_invalid_amount_formats(self, invalid_input):
        with pytest.raises(InvalidAmountFormatError):
            Amount.from_string(invalid_input)

class TestAccount:
    def test_valid_account(self):
        account = Account.from_string("Revolut LT603250052551241431-PLN")
        assert account.bank_name == "Revolut"
        assert account.account_number == "LT603250052551241431"
        assert account.currency == "PLN"

    @pytest.mark.parametrize("invalid_input", [
        "Revolut-LT603250052551241431-PLN",  # Wrong separator
        "Revolut LT603250052551241431PLN",  # Missing currency separator
        "Revolut",  # Incomplete
        "Revolut-PLN",  # Missing account number
        "",  # Empty string
        "Revolut LT603250052551241431-PLNN",  # Invalid currency
    ])
    def test_invalid_account_formats(self, invalid_input):
        with pytest.raises(ParserError):
            Account.from_string(invalid_input)

class TestTransaction:
    @pytest.fixture
    def sample_transaction(self):
        return Transaction(
            category="Books, audio, subscriptions",
            account=Account("Revolut", "LT603250052551241431", "PLN"),
            merchant_name="Spotify",
            merchant_description="Spotify Premium",
            amount=Amount(Decimal("-37.99"), "PLN")
        )

    def test_is_income(self, sample_transaction):
        assert not sample_transaction.is_income()
        
        income_transaction = Transaction(
            category="Income",
            account=sample_transaction.account,
            merchant_name="Salary",
            merchant_description="Monthly salary",
            amount=Amount(Decimal("5000.00"), "PLN")
        )
        assert income_transaction.is_income()

class TestParser:
    @pytest.fixture
    def parser(self):
        return TransactionParser(current_year=2023)

    def test_parse_empty_input(self, parser):
        assert parser.parse("") == []
        assert parser.parse("\n\n  \n") == []

    def test_parse_single_day(self, parser):
        input_text = """
        December 12
        PLN 59.08
        Books, audio, subscriptions
        Revolut LT603250052551241431-PLN
        Spotify
        Spotify Premium
        -PLN 37.99
        """
        result = parser.parse(input_text)
        assert len(result) == 1
        assert result[0].date == datetime(2023, 12, 12)
        assert result[0].running_balance.value == Decimal("59.08")
        assert len(result[0].transactions) == 1

    def test_parse_multiple_days(self, parser):
        input_text = """
        December 12
        PLN 59.08
        Books, audio, subscriptions
        Revolut LT603250052551241431-PLN
        Spotify
        Spotify Premium
        -PLN 37.99
        
        December 11
        PLN 100.00
        Income
        Revolut LT603250052551241431-PLN
        Salary
        Monthly salary
        PLN 5000.00
        """
        result = parser.parse(input_text)
        assert len(result) == 2
        assert [len(day.transactions) for day in result] == [1, 1]

    def test_missing_running_balance(self, parser):
        input_text = """
        December 12
        Books, audio, subscriptions
        Revolut LT603250052551241431-PLN
        Spotify
        Spotify Premium
        -PLN 37.99
        """
        result = parser.parse(input_text)
        assert len(result) == 1
        assert result[0].running_balance is None

    def test_incomplete_transaction(self, parser):
        input_text = """
        December 12
        PLN 59.08
        Books, audio, subscriptions
        Revolut LT603250052551241431-PLN
        Spotify
        """
        result = parser.parse(input_text)
        assert len(result) == 1
        assert len(result[0].transactions) == 0

    def test_mixed_currencies(self, parser):
        input_text = """
        December 12
        PLN 59.08
        Books, audio, subscriptions
        Revolut LT603250052551241431-PLN
        Spotify
        Spotify Premium
        -PLN 37.99
        
        Entertainment
        Revolut LT603250052551241431-EUR
        Netflix
        Netflix Premium
        -EUR 15.99
        """
        result = parser.parse(input_text)
        assert not parser.validate_parsed_data(result)

    @pytest.mark.parametrize("date_str", [
        "January 1",
        "February 28",
        "March 31",
        "December 31",
    ])
    def test_valid_dates(self, parser, date_str):
        input_text = f"""
        {date_str}
        PLN 100.00
        """
        result = parser.parse(input_text)
        assert len(result) == 1

    def test_malformed_data_recovery(self, parser):
        input_text = """
        December 12
        PLN 59.08
        Invalid line
        More invalid data
        
        December 11
        PLN 100.00
        Books, audio, subscriptions
        Revolut LT603250052551241431-PLN
        Spotify
        Spotify Premium
        -PLN 37.99
        """
        result = parser.parse(input_text)
        assert len(result) == 2
        assert len(result[0].transactions) == 0
        assert len(result[1].transactions) == 1

class TestDataValidation:
    @pytest.fixture
    def parser(self):
        return TransactionParser(current_year=2023)

    def test_validate_balanced_transactions(self, parser):
        daily = DailyTransactions(
            date=datetime(2023, 12, 12),
            running_balance=Amount(Decimal("62.01"), "PLN"),
            transactions=[
                Transaction(
                    category="Income",
                    account=Account("Revolut", "LT123", "PLN"),
                    merchant_name="Salary",
                    merchant_description="Monthly",
                    amount=Amount(Decimal("100.00"), "PLN")
                ),
                Transaction(
                    category="Expenses",
                    account=Account("Revolut", "LT123", "PLN"),
                    merchant_name="Shop",
                    merchant_description="Shopping",
                    amount=Amount(Decimal("-37.99"), "PLN")
                ),
            ]
        )
        assert parser.validate_parsed_data([daily])

    def test_validate_unbalanced_transactions(self, parser):
        daily = DailyTransactions(
            date=datetime(2023, 12, 12),
            running_balance=Amount(Decimal("100.00"), "PLN"),
            transactions=[
                Transaction(
                    category="Expenses",
                    account=Account("Revolut", "LT123", "PLN"),
                    merchant_name="Shop",
                    merchant_description="Shopping",
                    amount=Amount(Decimal("-37.99"), "PLN")
                ),
            ]
        )
        assert not parser.validate_parsed_data([daily])


def test_october_transactions_count():
    # Test data
    test_data = """
    October 10
    -PLN 255.71
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Katarzyna Kowalczyk
    Katarzyna Kowalczyk
    -PLN 13.00
    Health care, doctor
     Revolut LT603250052551241431-PLN
    Apteka Medicover
    Apteka Medicover
    -PLN 173.69
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Zabka Z9476 K.2
    Zabka Z9476 K.2
    -PLN 1.40
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Zabka Z9476 K.2
    Zabka Z9476 K.2
    -PLN 24.98
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Bolt.eu/o/2410100717
    bolt.eu/o/2410100717
    -PLN 42.64
    October 8
    PLN 496.80
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Bilety Urbancard Wrocl
    Bilety Urbancard Wrocl
    -PLN 3.20
    Income
     Revolut LT603250052551241431-PLN
    Top-Up by *5193
    PLN 500.00
    October 4
    -PLN 26.90
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Etsy.com*jaznjezarts
    Etsy.com*jaznjezarts
    -PLN 22.90
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Bilety Urbancard Wrocl
    Bilety Urbancard Wrocl
    -PLN 4.00
    October 3
    -PLN 111.03
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Google *google One
    Google *google One
    -PLN 89.99
    Budowlane
     Revolut LT603250052551241431-PLN
    Action A054
    Action A054
    -PLN 8.78
    Income
     Revolut LT603250052551241431-PLN
    Refund from Allegro
    PLN 119.00
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    As Vending Wroclaw
    As Vending Wroclaw
    -PLN 3.50
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Cockpeat
    Cockpeat
    -PLN 35.00
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Cockpeat
    Cockpeat
    -PLN 24.00
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Bolt.eu/o/2410030722
    bolt.eu/o/2410030722
    -PLN 23.56
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Bolt.eu/o/2410030707
    bolt.eu/o/2410030707
    -PLN 20.63
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Bolt.eu/o/2410030624
    bolt.eu/o/2410030624
    -PLN 24.57
    October 2
    -PLN 104.13
    TV, Streaming
     Revolut LT603250052551241431-PLN
    Openai
    Openai
    -PLN 39.15
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Apple.com/bill
    apple.com/bill
    -PLN 29.99
    Holiday, trips, hotels
     Revolut LT603250052551241431-PLN
    Apple.com/bill
    apple.com/bill
    -PLN 34.99
    """

    parser = TransactionParser()
    result = parser.parse(test_data)

    # Expected number of transactions per day
    expected_transactions = {
        "October 10": 5,  # 5 transactions
        "October 8": 2,   # 2 transactions (including Top-Up)
        "October 4": 2,   # 2 transactions
        "October 3": 9,   # 9 transactions (including Refund)
        "October 2": 3,   # 3 transactions
    }

    # Verify results
    assert len(result) == 5, "Should have 5 days of transactions"

    for day in result:
        date_key = day.date.strftime("%B %d")
        assert len(day.transactions) == expected_transactions[date_key], \
            f"Incorrect number of transactions for {date_key}. " \
            f"Expected {expected_transactions[date_key]}, got {len(day.transactions)}"

    # Verify total number of transactions
    total_transactions = sum(len(day.transactions) for day in result)
    assert total_transactions == 21, "Total number of transactions should be 21"

def test_october_transactions_details():
    """Additional test to verify specific transaction details"""
    parser = TransactionParser()
    result = parser.parse(test_data)

    # Verify first day (October 10) first transaction
    oct_10 = result[0]
    assert oct_10.date.day == 10
    assert oct_10.date.month == 10
    assert oct_10.running_balance.value == Decimal("-255.71")

    first_transaction = oct_10.transactions[0]
    assert first_transaction.category == "Holiday, trips, hotels"
    assert first_transaction.merchant_name == "Katarzyna Kowalczyk"
    assert first_transaction.amount.value == Decimal("-13.00")

    # Verify last day (October 2) last transaction
    oct_2 = result[-1]
    assert oct_2.date.day == 2
    assert oct_2.date.month == 10

    last_transaction = oct_2.transactions[-1]
    assert last_transaction.category == "Holiday, trips, hotels"
    assert last_transaction.merchant_name == "Apple.com/bill"
    assert last_transaction.amount.value == Decimal("-34.99")

