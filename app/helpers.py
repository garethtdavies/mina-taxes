import base58
from dateutil.parser import parse


class Config():
    """
    A place to define the constants used throughout the application.
    """
    def constants(self):
        return {
            'genesis_date': '2021-06-01T00:00:00Z',
            'genesis_ledger_hash':
            'jx7buQVWFLsXTtzRgSxbYcT8EYLS8KCZbLrfDcJxMtyy4thw2Ee',
            'genesis_state_hash':
            '3NKeMoncuHab5ScarV5ViyF16cJPT4taWNSaTLS64Dp67wuXigPZ',
            'pre_trading_value': 0.25,
            'pool_payout_keyword': 'Payout',
        }


class TaxTools():
    """
    A class for helper functions for all tax exporters.
    """
    def memo_parser(self, memo):
        """Decode the memo output"""
        decoded = base58.b58decode(memo)
        decoded = decoded[3:-4]
        output = decoded.decode("utf-8", "ignore")
        output = output.strip()
        return output.replace("\x00", "")

    def mina_format(self, s):
        """Format nanomina to mina"""
        return s / 1000000000

    def calculate_net_worth(self, tx_date, amount=None):
        """Consider all values before trading started as a flat rate"""
        started_trading = parse(Config().constants()["genesis_date"])

        tx_date_time = tx_date
        if tx_date_time < started_trading:
            net_worth = Config().constants(
            )["pre_trading_value"] * self.mina_format(amount)
        else:
            net_worth = ""

        return net_worth