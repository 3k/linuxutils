#!/usr/bin/env python
# coding: utf8

import csv, itertools, sys, os, locale, operator, collections
from decimal import Decimal
import texttable    # pip install texttable


class CommentedFile(object):
    """The new montyly payout reports available since 2012 now have comments
    in them. The older "sales reports" did not.

    http://bugs.python.org/msg48505"""
    def __init__(self, f, commentstring="#"):
        self.f = f
        self.commentstring = commentstring
    def next(self):
        line = self.f.next()
        while line.startswith(self.commentstring):
            line = self.f.next()
        return line
    def __iter__(self):
        return self


def read_csv(file):
    with open(file, 'r') as f:
        return list(csv.DictReader(CommentedFile(f), delimiter=','))


def group_by(records, key):
    """For a payout report, returns a structure like:

      {'DE': {'charged': 15,
              'received': 10,
              'num_sales': 3},
       'US': {...},
       ...

    All values are in seller's currency (yours).

    In case this is an "estimtaed sales" report, it will not contain the
    "received" key, and the value in "charged" will be the buyer's currency.
    """
    # itertools.groupby requires sorted input
    records.sort(key=key)

    result = collections.OrderedDict()
    for country, sales in itertools.groupby(records, key=key):
        sales = list(sales)

        """
        TODO: There actually seems to be a bug in both payout and sales
        reports, where I have buyers from the US paying in KRW, and no FX Rate
        is given. In those cases, assuming 1 as FX rate is wrong. Example:

        {'Merchant Currency': 'KRW', 'Country of Buyer': 'US', ..., 'Merchant Receives': '0.00', 'Item Price': '1,165.00', 'Charged Amount': '1,165.00', 'Order Charged Date': '2012-04-18', 'Currency of Sale': 'KRW', 'City of Buyer': 'Honolulu', 'Estimated FX Rate': '', 'State of Buyer': 'HI', ... 'Financial Status': 'Charged'}
        """

        received = lambda s: Decimal(str(locale.atof(s['Amount (Merchant Currency)'])))

        result[country] = {
          'num_sales': len(list(sales)),
          'received': sum([received(s) for s in sales])
        }

    # Without a single currency, sum makes no sense
    result['SUM'] = reduce(operator.add, map(collections.Counter, result.values()))

    return result


if __name__ == '__main__':
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

    # define different keys
    country = lambda x: x['Buyer Country']
    eu_codes = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'EL', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE']
    euvat = lambda x: 'EU' if x['Buyer Country'] in eu_codes else 'Non-EU'

    for filename in sorted(sys.argv[1:]):
        print os.path.basename(filename)
        records = read_csv(filename)

        table = texttable.Texttable()        
        #table.set_deco(texttable.Texttable.HEADER)
        table.set_cols_dtype(['t', 'i', 't', 't'])
        table.set_cols_align(["l", 'r', "r", "r"])
        table.header(['', 'Num', 'Received', '19%'])
        key_to_use = euvat


        for country, data in sorted(group_by(records, key_to_use).items(), key=lambda t: t[1]):
            table.add_row([
                country,
                data['num_sales'],
                '%.2f €' % data['received'] if 'received' in data else '-',
                '%.2f €' % (data['received'] / Decimal('1.19') * Decimal('0.19')) if 'received' in data else '-',
            ])

        # Indent table by 4 spaces
        print 4 * ' ' + table.draw().replace('\n', '\n' + (4 * ' '))
