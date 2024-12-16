from dataclasses import dataclass
from typing import List, TextIO
import csv
from datetime import datetime
import io


from .parser import Transaction, Amount, DailyTransactions

class TransactionCsvExporter:
    def __init__(self, date_format: str = "%m/%d/%Y"):
        self.date_format = date_format

    def _format_memo(self, transaction: Transaction) -> str:
        """Format memo field from category and merchant info"""
        category = getattr(transaction, 'category', '')  # Handle optional category
        if category:
            return f"{category} - {transaction.merchant_name}"
        return transaction.merchant_name

    def _get_amount_fields(self, amount: Amount) -> tuple[float, float]:
        """Returns (outflow, inflow) tuple based on amount"""
        value = float(abs(amount.value))
        return (value, 0) if amount.value < 0 else (0, value)

    def export_to_csv(self, daily_transactions: List[DailyTransactions], output: TextIO) -> None:
        """Export transactions to CSV file"""
        writer = csv.writer(output)
        # Write header
        writer.writerow(['Date', 'Payee', 'Memo', 'Outflow', 'Inflow'])

        # Write transactions
        for daily in daily_transactions:
            for tx in daily.transactions:
                outflow, inflow = self._get_amount_fields(tx.amount)
                writer.writerow([
                    daily.date.strftime(self.date_format),
                    '',  # Payee (empty in your example)
                    self._format_memo(tx),
                    f"{outflow:.2f}" if outflow else '',
                    f"{inflow:.2f}" if inflow else ''
                ])
