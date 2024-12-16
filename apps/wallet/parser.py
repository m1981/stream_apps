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
            value=Decimal('-' + value if sign else value),
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
        current_transactions = []
        running_balance = None
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        i = 0
        
        while i < len(lines):
            try:
                # Try to parse as date
                current_date = self.parse_date(lines[i])
                
                # Save previous day if exists
                if current_day:
                    result.append(DailyTransactions(
                        date=current_day,
                        running_balance=running_balance,
                        transactions=current_transactions
                    ))
                
                current_day = current_date
                current_transactions = []
                running_balance = None
                i += 1
                
                # Check for running balance
                if i < len(lines) and 'PLN' in lines[i]:
                    running_balance = Amount.from_string(lines[i])
                    i += 1
                
                continue
                
            except ValueError:
                pass
            
            # Skip category and account lines
            while i < len(lines) and not lines[i].startswith('PLN') and not lines[i].startswith('-PLN'):
                i += 1
                
            if i + 2 >= len(lines):
                break
                
            # Parse transaction
            amount = Amount.from_string(lines[i])
            merchant_name = lines[i-2]
            merchant_desc = lines[i-1]
            
            current_transactions.append(Transaction(
                merchant_name=merchant_name,
                merchant_description=merchant_desc,
                amount=amount
            ))
            
            i += 1
            
        # Don't forget last day
        if current_day and current_transactions:
            result.append(DailyTransactions(
                date=current_day,
                running_balance=running_balance,
                transactions=current_transactions
            ))
            
        return result

