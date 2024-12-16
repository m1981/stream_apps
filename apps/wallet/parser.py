from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import re
from enum import Enum

@dataclass
class Amount:
    value: Decimal
    currency: str

    @classmethod
    def from_string(cls, amount_str: str) -> 'Amount':
        """Parse amount string like '-PLN 40.92' or 'PLN 100.00'"""
        match = re.match(r'^(-)?([A-Z]{3})\s+(\d+\.?\d*)$', amount_str.strip())
        if not match:
            raise ValueError(f"Invalid amount format: {amount_str}")
        sign, currency, value = match.groups()
        return cls(
            value=Decimal(f"{'-' if sign else ''}{value}"),
            currency=currency
        )

@dataclass
class Transaction:
    merchant_name: str
    merchant_description: str
    amount: Amount
    
@dataclass
class DailyTransactions:
    date: datetime
    running_balance: Optional[Amount]
    transactions: List[Transaction]

class TransactionParser:
    @staticmethod
    def parse_date(date_str: str) -> datetime:
        return datetime.strptime(date_str, "%B %d")
    
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
            try:
                date = self.parse_date(line)
                if current_day:
                    result.append(DailyTransactions(
                        date=current_day,
                        running_balance=current_balance,
                        transactions=current_transactions
                    ))
                current_day = date
                current_balance = None
                current_transactions = []
                i += 1
                continue
            except ValueError:
                pass
            
            # Try parse as running balance
            try:
                if current_day and not current_balance:
                    current_balance = Amount.from_string(line)
                    i += 1
                    continue
            except ValueError:
                pass
            
            # Try parse transaction (need at least 3 lines)
            if i + 2 < len(lines):
                try:
                    amount = Amount.from_string(lines[i + 2])
                    transaction = Transaction(
                        merchant_name=lines[i],
                        merchant_description=lines[i + 1],
                        amount=amount
                    )
                    current_transactions.append(transaction)
                    i += 3
                    continue
                except ValueError:
                    pass
            
            i += 1
        
        # Don't forget last day
        if current_day:
            result.append(DailyTransactions(
                date=current_day,
                running_balance=current_balance,
                transactions=current_transactions
            ))
            
        return result