from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


class GraphQL():
    def __init__(self):
        self.transport = AIOHTTPTransport(
            url="https://graphql.minaexplorer.com")
        self.client = Client(transport=self.transport,
                             fetch_schema_from_transport=True)

    def get_transactions(self, address):
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
