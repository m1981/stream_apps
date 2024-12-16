# import unittest
# from datetime import datetime
# from decimal import Decimal
# from textwrap import dedent
#
# from formatter import TransactionExporter
# from parser import Transaction, TransactionType
#
# class TestTransactionExporter(unittest.TestCase):
#     def setUp(self):
#         self.exporter = TransactionExporter()
#         self.sample_transactions = [
#             Transaction(
#                 date=datetime(2023, 12, 7),
#                 amount=Decimal("-50.00"),
#                 category="Transfer",
#                 account="Revolut LT603250052551241431-PLN",
#                 merchant_name="Przelew na telefon BLIK",
#                 merchant_detail="Transfer out",
#                 transaction_type=TransactionType.EXPENSE
#             ),
#             Transaction(
#                 date=datetime(2023, 12, 6),
#                 amount=Decimal("460.00"),
#                 category="Income",
#                 account="Revolut LT603250052551241431-PLN",
#                 merchant_name="Micha? Jerzy Nakiewicz",
#                 merchant_detail="Przelew na telefon BLIK",
#                 transaction_type=TransactionType.INCOME
#             )
#         ]
#
#     def test_convert_transaction_expense(self):
#         transaction = self.sample_transactions[0]
#         csv_transaction = self.exporter.convert_transaction(transaction)
#
#         self.assertEqual(csv_transaction.date, datetime(2023, 12, 7))
#         self.assertEqual(csv_transaction.payee, "Przelew na telefon BLIK")
#         self.assertEqual(csv_transaction.memo, "Transfer out")
#         self.assertEqual(csv_transaction.outflow, Decimal("50.00"))
#         self.assertIsNone(csv_transaction.inflow)
#
#     def test_convert_transaction_income(self):
#         transaction = self.sample_transactions[1]
#         csv_transaction = self.exporter.convert_transaction(transaction)
#
#         self.assertEqual(csv_transaction.date, datetime(2023, 12, 6))
#         self.assertEqual(csv_transaction.payee, "Micha? Jerzy Nakiewicz")
#         self.assertEqual(csv_transaction.memo, "Przelew na telefon BLIK")
#         self.assertIsNone(csv_transaction.outflow)
#         self.assertEqual(csv_transaction.inflow, Decimal("460.00"))
#
#     def test_export_to_csv(self):
#         expected_csv = dedent("""\
#             Date,Payee,Memo,Outflow,Inflow
#             12/07/2023,Przelew na telefon BLIK,Transfer out,50.00,
#             12/06/2023,Micha? Jerzy Nakiewicz,Przelew na telefon BLIK,,460.00
#             """)
#
#         result = self.exporter.export_to_csv(self.sample_transactions)
#         self.assertEqual(result, expected_csv)
#
#     def test_export_empty_transactions(self):
#         expected_csv = "Date,Payee,Memo,Outflow,Inflow\n"
#         result = self.exporter.export_to_csv([])
#         self.assertEqual(result, expected_csv)
#
#     def test_export_to_file(self):
#         import tempfile
#         import os
#
#         with tempfile.NamedTemporaryFile(delete=False) as tmp:
#             self.exporter.export_to_file(self.sample_transactions, tmp.name)
#
#             with open(tmp.name, 'r') as f:
#                 content = f.read()
#
#         os.unlink(tmp.name)
#
#         expected_csv = dedent("""\
#             Date,Payee,Memo,Outflow,Inflow
#             12/07/2023,Przelew na telefon BLIK,Transfer out,50.00,
#             12/06/2023,Micha? Jerzy Nakiewicz,Przelew na telefon BLIK,,460.00
#             """)
#
#         self.assertEqual(content, expected_csv)
#
# if __name__ == '__main__':
#     unittest.main()
