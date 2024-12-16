import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import io
from .parser import Transaction

@dataclass
class CsvTransaction:
    date: datetime
    payee: str
    memo: str
    outflow: Optional[Decimal]
    inflow: Optional[Decimal]

class TransactionExporter:
    def __init__(self):
        self.headers = ["Date", "Payee", "Memo", "Outflow", "Inflow"]

    def convert_transaction(self, transaction: Transaction) -> CsvTransaction:
        """Convert Transaction to CsvTransaction format"""
        amount = transaction.amount
        
        return CsvTransaction(
            date=transaction.date,
            payee=transaction.merchant_name,
            memo=transaction.merchant_detail,
            outflow=abs(amount) if amount < 0 else None,
            inflow=amount if amount > 0 else None
        )

    def export_to_csv(self, transactions: List[Transaction]) -> str:
        """Export transactions to CSV string"""
        output = io.StringIO()
        writer = csv.writer(output, lineterminator='\n')
        
        # Write headers
        writer.writerow(self.headers)
        
        # Convert and write transactions
        for transaction in transactions:
            csv_transaction = self.convert_transaction(transaction)
            writer.writerow([
                csv_transaction.date.strftime("%m/%d/%Y"),
                csv_transaction.payee,
                csv_transaction.memo,
                f"{csv_transaction.outflow:.2f}" if csv_transaction.outflow else "",
                f"{csv_transaction.inflow:.2f}" if csv_transaction.inflow else ""
            ])
        
        return output.getvalue()

    def export_to_file(self, transactions: List[Transaction], filepath: str) -> None:
        """Export transactions to CSV file"""
        with open(filepath, 'w', newline='') as f:
            f.write(self.export_to_csv(transactions))
