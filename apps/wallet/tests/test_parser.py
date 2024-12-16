import pytest
from decimal import Decimal

from parser import TransactionParser, Amount, Transaction, DailyTransactions

def test_amount_parsing():
    assert Amount.from_string("PLN 100.00") == Amount(Decimal("100.00"), "PLN")
    assert Amount.from_string("-PLN 40.92") == Amount(Decimal("-40.92"), "PLN")

    with pytest.raises(ValueError):
        Amount.from_string("Invalid")
        
def test_single_day_parsing():
    text = """
    December 12
    PLN 59.08
    Merchant1
    Description1
    -PLN 40.92
    """
    
    parser = TransactionParser()
    result = parser.parse(text)
    
    assert len(result) == 1
    assert result[0].date.month == 12
    assert result[0].date.day == 12
    assert result[0].running_balance == Amount(Decimal("59.08"), "PLN")
    assert len(result[0].transactions) == 1
    assert result[0].transactions[0].amount == Amount(Decimal("-40.92"), "PLN")

def test_multiple_transactions_per_day():
    text = """
    December 12
    PLN 59.08
    Merchant1
    Description1
    -PLN 40.92
    Merchant2
    Description2
    PLN 100.00
    """
    
    parser = TransactionParser()
    result = parser.parse(text)
    
    assert len(result) == 1
    assert len(result[0].transactions) == 2

def test_multiple_days():
    text = """
    December 12
    PLN 59.08
    Merchant1
    Description1
    -PLN 40.92
    December 11
    Merchant2
    Description2
    -PLN 16.00
    """
    
    parser = TransactionParser()
    result = parser.parse(text)
    
    assert len(result) == 2
    assert result[0].date.day == 12
    assert result[1].date.day == 11

def test_empty_input():
    parser = TransactionParser()
    assert parser.parse("") == []

def test_malformed_input():
    text = """
    December 12
    Invalid amount
    Merchant1
    Description1
    """
    
    parser = TransactionParser()
    with pytest.raises(ValueError):
        parser.parse(text)
