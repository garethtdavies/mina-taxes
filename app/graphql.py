from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


class GraphQL():
    """
    Class to define the GraphQL queries used by exporters.
    """
    def __init__(self):
        """Define the GraphQL connection"""
        self.transport = AIOHTTPTransport(
            url="https://graphql.minaexplorer.com", timeout=60)
        self.client = Client(transport=self.transport,
                             fetch_schema_from_transport=True,
                             execute_timeout=60)

    def get_first_transaction_received(self, address):
        """Determines the first transaction received by an address"""

        first_transaction = gql("""
                  query firstTransaction($account: String!) {
                    transactions(limit: 1, sortBy: DATETIME_ASC, query: {to: $account, canonical: true}) {
                        dateTime
                        from
                        to
                        amount
                        hash
                        kind
                        block {
                            blockHeight
                            stateHash
                        }
                    }
                  }
                  """)

        params = {"account": address}

        result_first_transaction = self.client.execute(first_transaction,
                                                       variable_values=params)

        return result_first_transaction

    def get_transactions(self, address, start_date, end_date):
        """Get all transaction data for a given address."""
        transactions = gql("""
                query allTransactions($account: String!, $start_date: DateTime!, $end_date: DateTime!) {
                    transactions(limit: 100000, sortBy: DATETIME_ASC, query: {dateTime_gte: $start_date, dateTime_lt: $end_date, canonical: true, OR: [{to: $account}, {from: $account}]}) {
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

        params = {
            "account": address,
            "start_date": start_date,
            "end_date": end_date
        }

        result = self.client.execute(transactions, variable_values=params)

        return result

    def get_genesis_info(self, address):
        """Determines balance information for an account in the Genesis ledger."""
        genesis_ledger = gql("""
                  query genesisLedger($account: String!) {
                      stake(query: {public_key: $account, ledgerHash: "jx7buQVWFLsXTtzRgSxbYcT8EYLS8KCZbLrfDcJxMtyy4thw2Ee"}) {
                      ledgerHash
                      balance
                      }
                  }
                  """)

        params = {"account": address}

        result_genesis = self.client.execute(genesis_ledger,
                                             variable_values=params)

        return result_genesis

    def get_blocks_produced(self, address, start_date, end_date):
        """Determines fee transfers to an address, which would normally be the coinbase receiver"""

        blocks = gql("""
                  query allBlocks($account: String!, $start_date: DateTime!, $end_date: DateTime!) {
                    blocks(query: {dateTime_gte: $start_date, dateTime_lt: $end_date, transactions: {coinbaseReceiverAccount: {publicKey: $account}}, canonical: true}, sortBy: DATETIME_ASC, limit: 100000) {
                        dateTime
                        stateHash
                        blockHeight
                        canonical
                        txFees
                        snarkFees
                        transactions {
                        coinbase
                        }
                    }
                  }
                  """)

        params = {
            "account": address,
            "start_date": start_date,
            "end_date": end_date
        }

        result_blocks = self.client.execute(blocks, variable_values=params)

        return result_blocks

    def get_snarks_sold(self, address, start_date, end_date):
        """Determines fee transfers to an address, which would normally be the coinbase receiver"""

        snarks = gql("""
                  query allSnarks($account: String!, $start_date: DateTime!, $end_date: DateTime!) {
                    snarks(limit: 100000, sortBy: DATETIME_ASC, query: {dateTime_gte: $start_date, dateTime_lt: $end_date, canonical: true, prover: $account}) {
                    dateTime
                    blockHeight
                    fee
                    }
                  }
                  """)

        params = {
            "account": address,
            "start_date": start_date,
            "end_date": end_date
        }

        result_snarks = self.client.execute(snarks, variable_values=params)

        return result_snarks