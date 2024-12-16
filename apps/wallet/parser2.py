from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple, Pattern
import re
from enum import Enum
from collections import namedtuple

class ParserError(Exception):
    """Base exception for parser errors"""
    pass

class InvalidDateFormatError(ParserError):
    pass

class InvalidAmountFormatError(ParserError):
    pass

class InvalidTransactionFormatError(ParserError):
    pass

@dataclass(frozen=True)
class Amount:
    value: Decimal
    currency: str
    
    AMOUNT_PATTERN: Pattern = re.compile(r'^(-)?([A-Z]{3})\s+(\d+\.?\d*)$')
    
    @classmethod
    def from_string(cls, amount_str: str) -> 'Amount':
        """Parse amount string like '-PLN 40.92' or 'PLN 100.00'"""
        match = cls.AMOUNT_PATTERN.match(amount_str.strip())
        if not match:
            raise InvalidAmountFormatError(f"Invalid amount format: {amount_str}")
        
        sign, currency, value = match.groups()
        try:
            decimal_value = Decimal(f"{'-' if sign else ''}{value}")
            return cls(value=decimal_value, currency=currency)
        except (ValueError, DecimalException) as e:
            raise InvalidAmountFormatError(f"Invalid decimal value: {value}") from e

@dataclass(frozen=True)
class Account:
    bank_name: str
    account_number: str
    currency: str
    
    ACCOUNT_PATTERN: Pattern = re.compile(r'^([A-Za-z]+)\s+([A-Z0-9]+)-([A-Z]{3})$')
    
    @classmethod
    def from_string(cls, account_str: str) -> 'Account':
        """Parse account string like 'Revolut LT603250052551241431-PLN'"""
        match = cls.ACCOUNT_PATTERN.match(account_str.strip())
        if not match:
            raise ParserError(f"Invalid account format: {account_str}")
        
        bank, number, currency = match.groups()
        return cls(bank_name=bank, account_number=number, currency=currency)

@dataclass(frozen=True)
class Transaction:
    category: Optional[str]
    account: Account
    merchant_name: str
    merchant_description: str
    amount: Amount
    
    def is_income(self) -> bool:
        return self.amount.value > 0

@dataclass(frozen=True)
class DailyTransactions:
    date: datetime
    running_balance: Optional[Amount]
    transactions: List[Transaction]
    
    def total_income(self) -> Decimal:
        return sum(t.amount.value for t in self.transactions if t.is_income())
    
    def total_expense(self) -> Decimal:
        return sum(t.amount.value for t in self.transactions if not t.is_income())

class TransactionParser:
    def __init__(self, current_year: Optional[int] = None):
        self.current_year = current_year or datetime.now().year
    
    def parse_date(self, date_str: str) -> datetime:
        """Parse date string like 'December 12'"""
        try:
            date = datetime.strptime(date_str, "%B %d")
            return date.replace(year=self.current_year)
        except ValueError as e:
            raise InvalidDateFormatError(f"Invalid date format: {date_str}") from e
    
    def is_date_line(self, line: str) -> bool:
        try:
            self.parse_date(line)
            return True
        except InvalidDateFormatError:
            return False
    
    def is_amount_line(self, line: str) -> bool:
        try:
            Amount.from_string(line)
            return True
        except InvalidAmountFormatError:
            return False
    
    def parse_transaction_block(self, lines: List[str], start_idx: int) -> Tuple[Optional[Transaction], int]:
        """
        Parse a single transaction block, return (transaction, next_index)
        Returns (None, next_index) if no valid transaction could be parsed
        """
        if start_idx + 4 >= len(lines):
            return None, start_idx + 1
        
        try:
            # Check if this is a category or account line
            first_line = lines[start_idx].strip()
            if first_line.startswith('Revolut'):
                category = None
                account_idx = start_idx
            else:
                category = first_line
                account_idx = start_idx + 1
                
            if account_idx + 3 >= len(lines):
                return None, start_idx + 1
                
            account = Account.from_string(lines[account_idx])
            amount = Amount.from_string(lines[account_idx + 3])
            
            transaction = Transaction(
                category=category,
                account=account,
                merchant_name=lines[account_idx + 1],
                merchant_description=lines[account_idx + 2],
                amount=amount
            )
            
            return transaction, account_idx + 4
            
        except (ParserError, InvalidAmountFormatError):
            return None, start_idx + 1
    
    def parse(self, text: str) -> List[DailyTransactions]:
        result = []
        current_day = None
        current_balance = None
        current_transactions = []
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Try parse as date
            if self.is_date_line(line):
                if current_day:
                    result.append(DailyTransactions(
                        date=current_day,
                        running_balance=current_balance,
                        transactions=current_transactions
                    ))
                current_day = self.parse_date(line)
                current_balance = None
                current_transactions = []
                i += 1
                continue
            
            # Try parse as running balance
            if current_day and not current_balance and self.is_amount_line(line):
                current_balance = Amount.from_string(line)
                i += 1
                continue
            
            # Try parse transaction
            transaction, next_idx = self.parse_transaction_block(lines, i)
            if transaction:
                current_transactions.append(transaction)
            i = next_idx
        
        # Don't forget last day
        if current_day:
            result.append(DailyTransactions(
                date=current_day,
                running_balance=current_balance,
                transactions=current_transactions
            ))
            
        return result

    def validate_parsed_data(self, daily_transactions: List[DailyTransactions]) -> bool:
        """Validate parsed data for consistency"""
        for day in daily_transactions:
            if day.running_balance:
                # Validate that running balance matches transactions
                total = sum(t.amount.value for t in day.transactions)
                if abs(total - day.running_balance.value) > Decimal('0.01'):
                    return False
                
            # Validate all transactions have same currency
            currencies = {t.amount.currency for t in day.transactions}
            if len(currencies) > 1:
                return False
                
        return True
