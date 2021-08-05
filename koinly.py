import csv
import base58
from dateutil.parser import parse
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

transport = AIOHTTPTransport(url="https://graphql.minaexplorer.com")
client = Client(transport=transport, fetch_schema_from_transport=True)


# Parse the memo
def memo_parser(memo):
    """Decode the memo output"""
    decoded = base58.b58decode(memo)
    decoded = decoded[3:-4]
    output = decoded.decode("utf-8", "ignore")
    output = output.strip()
    return output.replace("\x00", "")


# Format the amounts
def mina_format(s):
    return s / 1000000000


# Determine if transaction was before trading started
def calculate_net_worth(tx_date, amount=None):

    # Consider all values before trading started on June 1st as $0.25
    started_trading = parse("2021-06-01T00:00:00Z")

    tx_date_time = parse(tx_date)
    if tx_date_time < started_trading:
        net_worth = 0.25 * mina_format(amount)
    else:
        net_worth = ""

    return net_worth


# The account to generate the Koinly import
account = "B62qkQJWnnDeWaqmBHsJ9ikLxsZfcdCtNhhRtrUnDfCe2Hzsqsu3RkV"

# Specify the headers for the Koinly import
header = [
    "Koinly Date", "Amount", "Currency", "Label", "TxHash", "Net Worth Amount",
    "Net Worth Currency", "Description"
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

params = {"account": account}

result = client.execute(transactions, variable_values=params)

# Determine if the account is in the genesis ledger
genesis_ledger = gql("""
      query genesisLedger($account: String!) {
        stake(query: {public_key: $account, epoch: 0}) {
          ledgerHash
        }
      }
      """)

result_genesis = client.execute(genesis_ledger, variable_values=params)

if not result_genesis["stake"]:
    burn_fee = True
else:
    burn_fee = False

with open('koinly-mina-tx.csv', 'w', encoding='UTF8') as f:
    writer = csv.writer(f)

    # write the header
    writer.writerow(header)

    i = 1

    # Loop through all transactions
    for tx in result["transactions"]:

        # Is this a withdrawal - if so include the fee and the balance as negative
        if tx["from"] == account:
            amount = -(tx["amount"] + tx["fee"])
        else:  # This is a deposit transaction
            amount = tx["amount"]

        # Is this a pool payout, if so label as REWARD
        # See labels here https://help.koinly.io/en/articles/3663453-what-are-labels
        if "Payout" in memo_parser(tx["memo"]):
            label = "reward"
        else:
            label = ""

        writer.writerow([
            tx["dateTime"],
            mina_format(amount), "MINA", label, tx["hash"],
            calculate_net_worth(tx["dateTime"], amount), "USD",
            memo_parser(tx["memo"])
        ])

        # After the first tx we may have burnt 1 MINA if the address was not in the Genesis ledger
        if i == 1 and burn_fee == True:
            writer.writerow([
                result["transactions"][0]["dateTime"], -1, "MINA", "",
                result["transactions"][0]["hash"],
                calculate_net_worth(tx["dateTime"],
                                    1000000000), "USD", "Ledger Fee"
            ])

        i += 1

print("Done")
