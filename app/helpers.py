import base58


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

    # Parse the memo
    def memo_parser(self, memo):
        """Decode the memo output"""
        decoded = base58.b58decode(memo)
        decoded = decoded[3:-4]
        output = decoded.decode("utf-8", "ignore")
        output = output.strip()
        return output.replace("\x00", "")

    # Format the amounts
    def mina_format(self, s):
        return s / 1000000000