import datetime
import os
import sys
import csv
import io
from unittest import TestCase

# Date,Payee,Category,Memo,Outflow,Inflow
# 17/10/2017,,,POL Wroclaw Brat Wurst,15.00,
# 17/10/2017,,,POL WROCLAW CARREFOUR EXPRESS 3721,,11.19

csv.register_dialect(u"alior_dialect", delimiter=u";")
csv.register_dialect(u"inteligo_dialect", delimiter=u",")
csv.register_dialect(u"millenium_dialect", delimiter=u",")

class YnabEntry(object):
    def __init__(self, date, payee, category, memo, amount, account):
        self.INTERNAL_TRANSFER_ALIOR_CREDIT = 'Transfer : Alior-czarna'
        self.INTERNAL_TRANSFER_ALIOR_DEBIT  = 'Transfer : Alior-biala'
        self.INTERNAL_TRANSFER_MILLENIUM  = 'Transfer : Milenium'
        self.INTERNAL_TRANSFER_ALIOR_KANTOR  = 'Transfer : Alior-kantor'

        assert date
        assert amount
        self.date = date
        self.memo = self._stripMemo(memo)
        # self.category = category
        self.category = self._deduceCategory(payee, memo, account)
        self.amount = amount
        self.payee = self._deducePayee(payee=payee, memo=self.memo, account=account)
        self.outflow = 0
        self.inflow = 0
        if amount > 0:
            self.inflow = amount
        else:
            self.outflow = amount

    def __str__(self):
        return '%s,%s,%s,%s,%s' % (self.date.strftime('%m/%d/%Y'), self.payee, self.category, self.memo, (str(abs(self.outflow))+',') if self.outflow else (','+str(abs(self.inflow))))


    def _stripMemo(self, memo):
        memo = memo.replace(';', ' ')
        memo = memo.replace(',', ' ')
        return memo

    def _deducePayee(self, payee, memo, account):
        return payee.strip() if payee  else ''

    def _deduceCategory(self, payee, memo, account):
        memo_upper = memo.upper()
        payee_upper = payee.upper() if payee else ""

        # First check payee for kids' names
        kids_categories = {
            'Lukasz': 'Dzieciaki: Lukasz',
            'Mateusz': 'Dzieciaki: Mateusz',
            'Kamila': 'Dzieciaki: Kamila'
        }

        # Check payee first for kids
        for kid_name, category in kids_categories.items():
            if kid_name.upper() in payee_upper:
                return category

        # Dictionary of categories with their corresponding keywords and matching rules
        memo_categories = {
            'Dzieciaki: Remonty': {
                'keywords': [
                    'BRICOMARCHE',
                    'LEROY MERLIN',
                    'MARKET OBI',
                    'OGOLNOBUDOWLANE'
                ],
                'exact_match': False
            },
            'Basic need: Transport': {
                'keywords': [
                    'ORLEN STACJA',
                    'ORLEN',
                    'BP STACJA',
                    'SHELL'
                ],
                'exact_match': False
            },
            'Basic need: Medical': {
                'keywords': [
                    'TARABULA',
                    'APTEKA',
                    'PHARMACY',
                    'MEDICARE'
                ],
                'exact_match': False
            }
        }

        # Check memo for other categories
        for category, rules in memo_categories.items():
            keywords = rules['keywords']
            exact_match = rules['exact_match']

            for keyword in keywords:
                keyword_upper = keyword.upper()
                if exact_match:
                    if keyword_upper == memo_upper:
                        return category
                else:
                    if keyword_upper in memo_upper:
                        return category

        return ''


# Date,Payee,Category,Memo,Outflow,Inflow
# 17/10/2017,,,POL Wroclaw Brat Wurst,15.00,
# 17/10/2017,,,POL WROCLAW CARREFOUR EXPRESS 3721,,11.19

class AbstractRorConverter(object):
    def __init__(self):
        self.list = []
        self.list.append('Date,Payee,Category,Memo,Outflow,Inflow')

    def load(self, alior_file):
        self.input_file = alior_file

    def getStr(self):
        return u'\n'.join(map(str, self.list)) + u'\n'

    def _getValidChars(self, string):
        # return ''.join([i if ord(i) < 128 else '.' for i in string])
        return string

    def getPayee(self, row):
        payee = row[self.FIELD_PAYEE].replace(',', '')
        return self._getValidChars(payee)

    def getAmount(self, row):
        amount = row[self.FIELD_AMOUNT]
        amount = amount.replace(',','.')
        try:
             amount = float(amount)
        except ValueError as e:
            print( 'amount: >>%s<<' % amount)
            print( 'row: %s' % row)
            print( 'pos: %s' % self.FIELD_AMOUNT)
        return amount

    def getAccountNumber(self, row):
        return row[self.FIELD_ACCOUNT_NUMBER].strip()

    def convertToYnab(self, start_from_row=0):
        with io.open(self.input_file, 'r', encoding=self.encoding) as csvfile:
            self.cvsreader = csv.reader(csvfile, dialect=self.dialect)
            for i, row in enumerate(self.cvsreader):
                if i == 0 or i < start_from_row:
                    continue
                try:
                    memo = self._getValidChars(self.getMemo(row))
                    date = self.getDate(row)
                    payee = self.getPayee(row)
                    entry = YnabEntry(date=date, payee=payee, category='', memo=memo, amount=self.getAmount(row), account=self.getAccountNumber(row))
                    self.list.append(entry)
                except:
                    print( 'Error while parsing row: {}\n{}'.format(i+1, row))
                    raise

class AliorNewRorConverter(AbstractRorConverter):
    def __init__(self):
        AbstractRorConverter.__init__(self)
        self.dialect = 'alior_dialect'
        self.encoding='windows-1250'
        self.FIELD_DELIMITER = ';'
        self.FIELD_DATE = 0
        self.FIELD_PAYEE = 2
        self.FIELD_PAYEE_TO = 3
        self.FIELD_AMOUNT = 7
        self.FIELD_MEMO1 = 4
        self.FIELD_ACCOUNT_NUMBER=8

    def getPayee(self, row):
        payee = row[self.FIELD_PAYEE].replace(',', '').strip()
        payee_to = row[self.FIELD_PAYEE_TO].replace(',', '').strip()
        return self._getValidChars(payee_to)


    def getMemo(self, row):
        memo = row[self.FIELD_MEMO1].strip()
        return memo


    def getDate(self, row):
        print(row[self.FIELD_DATE])
        return datetime.datetime.strptime(row[self.FIELD_DATE], '%d-%m-%Y')



class AliorNewCardConverter(AbstractRorConverter):
    def __init__(self):
        AbstractRorConverter.__init__(self)
        self.dialect = 'alior_dialect'
        self.encoding='windows-1250'
        self.FIELD_DELIMITER = ';'
        self.FIELD_DATE = 0
        self.FIELD_PAYEE = 2
        self.FIELD_AMOUNT = 7
        self.FIELD_MEMO1 = 4
        self.FIELD_ACCOUNT_NUMBER=0

    def getMemo(self, row):
        memo = row[self.FIELD_MEMO1].strip()
        return memo

    def getDate(self, row):
        return datetime.datetime.strptime(row[self.FIELD_DATE], '%d-%m-%Y')



class AliorRorConverter(AbstractRorConverter):
    def __init__(self):
        AbstractRorConverter.__init__(self)
        self.dialect = 'alior_dialect'
        self.encoding='windows-1250'
        self.FIELD_DELIMITER = ';'
        self.FIELD_DATE = 0
        self.FIELD_PAYEE = 2
        self.FIELD_PAYEE_TO = 3
        self.FIELD_AMOUNT = 9
        self.FIELD_MEMO1 = 4
        self.FIELD_ACCOUNT_NUMBER=0

    def getPayee(self, row):
        payee = row[self.FIELD_PAYEE].replace(',', '').strip()
        payee_to = row[self.FIELD_PAYEE_TO].replace(',', '').strip()

        return self._getValidChars(payee)

    def getMemo(self, row):
        memo = row[self.FIELD_MEMO1].strip()
        return memo

    def getDate(self, row):
        return datetime.datetime.strptime(row[self.FIELD_DATE], '%Y%m%d')



class AliorCardConverter(AbstractRorConverter):
    def __init__(self):
        AbstractRorConverter.__init__(self)
        self.dialect = 'alior_dialect'
        self.encoding='windows-1250'
        self.FIELD_DELIMITER = ';'
        self.FIELD_DATE = 0
        self.FIELD_PAYEE = 9
        self.FIELD_AMOUNT = 3
        self.FIELD_MEMO1 = 7
        self.FIELD_ACCOUNT_NUMBER=0

    def getMemo(self, row):
        memo = '%s' % (row[self.FIELD_MEMO1].strip())
        if not memo:
            memo = "Przelew albo prowizja?"
        return memo

    def getDate(self, row):
        return datetime.datetime.strptime(row[self.FIELD_DATE], '%Y-%m-%d')



import unittest

class TestYnabEntry(unittest.TestCase):
    def setUp(self):
        # This runs before each test
        self.default_date = datetime.datetime.now()
        self.default_account = "123456789"

    def create_entry(self, memo, amount=100.0, payee="Test Payee"):
        """Helper method to create YnabEntry instances"""
        return YnabEntry(
            date=self.default_date,
            payee=payee,
            category="",
            memo=memo,
            amount=amount,
            account=self.default_account
        )

    def test_home_improvement_category(self):
        """Test home improvement store categorization"""
        test_cases = [
            ("Zakup w BRICOMARCHE WROCLAW", "Dzieciaki: Remonty"),
            ("LEROY MERLIN MAGNOLIA", "Dzieciaki: Remonty"),
            ("MARKET OBI WROCLAW", "Dzieciaki: Remonty"),
            ("Sklep Ogolnobudowlane", "Dzieciaki: Remonty"),
        ]

        for memo, expected_category in test_cases:
            with self.subTest(memo=memo):
                entry = self.create_entry(memo)
                self.assertEqual(entry.category, expected_category)

    def test_transport_category(self):
        """Test transport related categorization"""
        test_cases = [
            ("ORLEN STACJA 1234", "Basic need: Transport"),
            ("ORLEN STACJA WROCLAW", "Basic need: Transport"),
        ]

        for memo, expected_category in test_cases:
            with self.subTest(memo=memo):
                entry = self.create_entry(memo)
                self.assertEqual(entry.category, expected_category)

    def test_medical_category(self):
        """Test medical related categorization"""
        test_cases = [
            ("TARABULA SP. Z O.O.", "Basic need: Medical"),
            ("TARABULA APTEKA", "Basic need: Medical"),
        ]

        for memo, expected_category in test_cases:
            with self.subTest(memo=memo):
                entry = self.create_entry(memo)
                self.assertEqual(entry.category, expected_category)

    def test_home_improvement_category(self):
        """Test home improvement store categorization"""
        test_cases = [
            ("Zakup w BRICOMARCHE WROCLAW", "Dzieciaki: Remonty"),
            ("LEROY MERLIN MAGNOLIA", "Dzieciaki: Remonty"),
            ("MARKET OBI WROCLAW", "Dzieciaki: Remonty"),
            ("Sklep Ogolnobudowlane", "Dzieciaki: Remonty"),
        ]

        for memo, expected_category in test_cases:
            with self.subTest(memo=memo):
                entry = self.create_entry(memo)
                self.assertEqual(entry.category, expected_category)

    def test_kids_category(self):
        """Test kids related categorization"""
        test_cases = [
            ("Some memo ", " Kamila Przelew", "Dzieciaki: Kamila"),
            ("Random  memo", "Lukasz", "Dzieciaki: Lukasz"),
            (" D", "Mateusz ABC", "Dzieciaki: Mateusz"),
        ]

        for memo, payee, expected_category in test_cases:
            with self.subTest(memo=memo, payee=payee):
                entry = self.create_entry(memo, payee=payee)
                self.assertEqual(entry.category, expected_category)

    def test_case_insensitivity(self):
        """Test that categorization is case-insensitive"""
        test_cases = [
            ("orlen STACJA", None, "Basic need: Transport"),
            ("Bricomarche", None, "Dzieciaki: Remonty"),
            ("Some memo", "KAMILA", "Dzieciaki: Kamila"),
            ("Some memo", "kamila", "Dzieciaki: Kamila"),
        ]

        for memo, payee, expected_category in test_cases:
            with self.subTest(memo=memo, payee=payee):
                entry = self.create_entry(memo, payee=payee)
                self.assertEqual(entry.category, expected_category)


    def test_edge_cases(self):
        """Test edge cases and potential problem scenarios"""
        test_cases = [
            ("ORLEN", None, "Basic need: Transport"),  # Emoji in memo
            ("ORLEN" * 100, None, "Basic need: Transport"),  # Very long memo
        ]

        for memo, payee, expected_category in test_cases:
            with self.subTest(memo=memo, payee=payee):
                entry = self.create_entry(memo, payee=payee)
                self.assertEqual(entry.category, expected_category)

    def test_case_insensitivity(self):
        """Test that categorization is case-insensitive"""
        test_cases = [
            ("orlen STACJA", "Basic need: Transport"),
            ("Bricomarche", "Dzieciaki: Remonty"),
        ]

        for memo, expected_category in test_cases:
            with self.subTest(memo=memo):
                entry = self.create_entry(memo)
                self.assertEqual(entry.category, expected_category)

    def test_special_characters(self):
        """Test handling of special characters in memo"""
        test_cases = [
            ("ORLEN-STACJA", "Basic need: Transport"),
            ("BRICOMARCHE/WROCLAW", "Dzieciaki: Remonty"),
        ]

        for memo, expected_category in test_cases:
            with self.subTest(memo=memo):
                entry = self.create_entry(memo)
                self.assertEqual(entry.category, expected_category)

    def test_multiple_matches_priority(self):
        """Test that category priority is respected when multiple matches are possible"""
        entry = self.create_entry("ORLEN KAMILA")  # Contains both ORLEN and KAMILA
        # You should define which category should take precedence and test for it
        expected_category = "Basic need: Transport"  # or whatever category should have priority
        self.assertEqual(entry.category, expected_category)

    def test_memo_stripping(self):
        """Test that memo stripping works correctly"""
        entry = self.create_entry("ORLEN STACJA; test, test")
        self.assertEqual(entry.memo, "ORLEN STACJA  test  test")

if __name__ == '__main__':
    unittest.main()

