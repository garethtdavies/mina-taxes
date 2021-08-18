from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


class GraphQL():
    """
    Class to define the GraphQL queries used by exporters.
    """
    def __init__(self):
        """Define the GraphQL connection"""
        self.transport = AIOHTTPTransport(
            url="https://graphql.minaexplorer.com")
        self.client = Client(transport=self.transport,
                             fetch_schema_from_transport=True)

    def get_transactions(self, address):
        """Get all transaction data for a given address."""
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

    def get_blocks_produced(self, address):
        """Determines fee transfers to an address, which would normally be the coinbase receiver"""

        blocks = gql("""
                  query allBlocks($account: String!) {
                    blocks(query: {transactions: {coinbaseReceiverAccount: {publicKey: $account}}, canonical: true}, sortBy: DATETIME_ASC, limit: 100000) {
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

        params = {"account": address}

        result_blocks = self.client.execute(blocks, variable_values=params)

        return result_blocks

    def get_snarks_sold(self, address):
        """Determines fee transfers to an address, which would normally be the coinbase receiver"""

        snarks = gql("""
                  query allSnarks($account: String!) {
                    snarks(limit: 100000, sortBy: DATETIME_ASC, query: {canonical: true, prover: $account}) {
                    dateTime
                    blockHeight
                    fee
                    }
                  }
                  """)

        params = {"account": address}

        result_snarks = self.client.execute(snarks, variable_values=params)

        return result_snarks