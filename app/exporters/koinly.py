import io
import csv
import base58
from dateutil.parser import parse
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


class Koinly():
    def __init__(self):
        self.transport = AIOHTTPTransport(
            url="https://graphql.minaexplorer.com")
        self.client = Client(transport=self.transport,
                             fetch_schema_from_transport=True)
        self.si = io.StringIO()
        self.writer = csv.writer(self.si)

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

    # Determine if transaction was before trading started
    def calculate_net_worth(self, tx_date, amount=None):

        # Consider all values before trading started on June 1st as $0.25
        started_trading = parse("2021-06-01T00:00:00Z")

        tx_date_time = parse(tx_date)
        if tx_date_time < started_trading:
            net_worth = 0.25 * self.mina_format(amount)
        else:
            net_worth = ""

        return net_worth

    def download_export(self, address):

        # Specify the headers for the Koinly import
        header = [
            "Koinly Date", "Amount", "Currency", "Label", "TxHash",
            "Net Worth Amount", "Net Worth Currency", "Description"
        ]

        # Get all the transaction data for this account
        transactions = gql("""
            query allTransactions($account: String!) {
                transactions(limit: 100000, sortBy: DATETIME_ASC, query: {canonical: true, OR: [{to: $account}, {from: $account}]}) {
                    fee
                    from
                    to
                    nonce
                    amount
                    memo
                    hash
                    kind
                    dateTime
                    block {
                        blockHeight
                        stateHash
                    }
                }
            }
            """)

        params = {"account": address}

        result = self.client.execute(transactions, variable_values=params)

        # Determine if the account is in the genesis ledger
        genesis_ledger = gql("""
            query genesisLedger($account: String!) {
                stake(query: {public_key: $account, epoch: 0}) {
                ledgerHash
                }
            }
            """)

        result_genesis = self.client.execute(genesis_ledger,
                                             variable_values=params)

        if not result_genesis["stake"]:
            burn_fee = True
        else:
            burn_fee = False

        # write the header
        self.writer.writerow(header)

        i = 1

        # Loop through all transactions
        for tx in result["transactions"]:

            # Is this a withdrawal - if so include the fee and the balance as negative
            if tx["from"] == address:
                amount = -(tx["amount"] + tx["fee"])
            else:  # This is a deposit transaction
                amount = tx["amount"]

            # Is this a pool payout, if so label as REWARD
            # See labels here https://help.koinly.io/en/articles/3663453-what-are-labels
            if "Payout" in self.memo_parser(tx["memo"]):
                label = "reward"
            else:
                label = ""

            self.writer.writerow([
                tx["dateTime"],
                self.mina_format(amount), "MINA", label, tx["hash"],
                self.calculate_net_worth(tx["dateTime"], amount), "USD",
                self.memo_parser(tx["memo"])
            ])

            # After the first tx we may have burnt 1 MINA if the address was not in the Genesis ledger
            if i == 1 and burn_fee == True:
                self.writer.writerow([
                    result["transactions"][0]["dateTime"], -1, "MINA", "",
                    result["transactions"][0]["hash"],
                    self.calculate_net_worth(tx["dateTime"],
                                             1000000000), "USD", "Ledger Fee"
                ])

            i += 1

        return (self.si.getvalue())
