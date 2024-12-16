import unittest
from decimal import Decimal

from parser import TransactionParser1, Amount, Transaction, DailyTransactions

class TestTransactionParser(unittest.TestCase):
    def setUp(self):
        self.parser = TransactionParser1()

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


    def test_real_data_sample(self):
        data = """
        December 12
        PLN 59.08
        Kamila
        Revolut LT603250052551241431-PLN
        Openai
        Openai
        -PLN 40.92
        Income
        Revolut LT603250052551241431-PLN
        Top-Up by *5193
        PLN 100.00
        December 11
        -PLN 16.00
        Books, audio, subscriptions
        Revolut LT603250052551241431-PLN
        Polityka.pl
        polityka.pl
        -PLN 16.00
        December 9
        -PLN 20.62
        Books, audio, subscriptions
        Revolut LT603250052551241431-PLN
        S4ynab* Trial Over
        S4ynab* Trial Over
        -PLN 20.62
        """

        result = self.parser.parse(data)

        # Test basic structure
        self.assertEqual(len(result), 3)  # 3 days

        # Test December 12
        dec12 = result[0]
        self.assertEqual(dec12.date.month, 12)
        self.assertEqual(dec12.date.day, 12)
        self.assertEqual(dec12.running_balance.value, Decimal('59.08'))
        self.assertEqual(len(dec12.transactions), 2)
        self.assertEqual(dec12.transactions[0].amount.value, Decimal('-40.92'))
        self.assertEqual(dec12.transactions[1].amount.value, Decimal('100.00'))

        # Test December 11
        dec11 = result[1]
        self.assertEqual(dec11.date.day, 11)
        self.assertEqual(dec11.running_balance.value, Decimal('-16.00'))
        self.assertEqual(len(dec11.transactions), 1)
        self.assertEqual(dec11.transactions[0].amount.value, Decimal('-16.00'))

        # Test December 9
        dec9 = result[2]
        self.assertEqual(dec9.date.day, 9)
        self.assertEqual(dec9.running_balance.value, Decimal('-20.62'))
        self.assertEqual(len(dec9.transactions), 1)
        self.assertEqual(dec9.transactions[0].merchant_name, 'S4ynab* Trial Over')
        self.assertEqual(dec9.transactions[0].amount.value, Decimal('-20.62'))

    def test_full_month_data(self):
        # This is a larger test case that you can use with more data
        data = """
        December 12
        PLN 59.08
        Kamila
        Revolut LT603250052551241431-PLN
        Openai
        Openai
        -PLN 40.92
        Income
        Revolut LT603250052551241431-PLN
        Top-Up by *5193
        PLN 100.00
        November 30
        -PLN 114.96
        Home, garden
        Revolut LT603250052551241431-PLN
        Action A054
        Action A054
        -PLN 26.75
        Health and beauty
        Revolut LT603250052551241431-PLN
        Rossmann 44
        Rossmann 44
        -PLN 288.21
        Income
        Revolut LT603250052551241431-PLN
        Top-Up by *5193
        PLN 200.00
        """

        result = self.parser.parse(data)

        # Test structure
        self.assertEqual(len(result), 2)  # 2 days

        # Test cross-month handling
        dec_data = result[0]
        nov_data = result[1]

        self.assertEqual(dec_data.date.month, 12)
        self.assertEqual(nov_data.date.month, 11)

        # Test November 30 transactions
        self.assertEqual(len(nov_data.transactions), 3)
        self.assertEqual(nov_data.running_balance.value, Decimal('-114.96'))

        # Verify specific transaction
        rossmann_transaction = [t for t in nov_data.transactions
                              if 'Rossmann' in t.merchant_name][0]
        self.assertEqual(rossmann_transaction.amount.value, Decimal('-288.21'))
