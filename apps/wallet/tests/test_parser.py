import unittest
from decimal import Decimal

from parser import TransactionParser, Amount, Transaction, DailyTransactions

class TestTransactionParser(unittest.TestCase):
    def setUp(self):
        self.parser = TransactionParser()

    def test_parse_simple_day(self):
        data = """
        December 12
        PLN 59.08
        Merchant1
        Merchant1 desc
        -PLN 40.92
        """
        result = self.parser.parse(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].date.month, 12)
        self.assertEqual(result[0].date.day, 12)
        self.assertEqual(result[0].running_balance.value, Decimal('59.08'))
        self.assertEqual(len(result[0].transactions), 1)
        self.assertEqual(result[0].transactions[0].amount.value, Decimal('-40.92'))

    def test_multiple_transactions_per_day(self):
        data = """
        December 12
        PLN 100.00
        Merchant1
        Desc1
        -PLN 40.00
        Merchant2
        Desc2
        -PLN 30.00
        """
        result = self.parser.parse(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0].transactions), 2)

    def test_day_without_balance(self):
        data = """
        December 12
        Merchant1
        Desc1
        -PLN 40.00
        """
        result = self.parser.parse(data)
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].running_balance)
        self.assertEqual(len(result[0].transactions), 1)

    def test_multiple_days(self):
        data = """
        December 12
        PLN 100.00
        Merchant1
        Desc1
        -PLN 40.00
        December 11
        PLN 50.00
        Merchant2
        Desc2
        -PLN 30.00
        """
        result = self.parser.parse(data)
        self.assertEqual(len(result), 2)

if __name__ == '__main__':
    unittest.main()
