import io
import csv
from app.graphql import GraphQL
import app.helpers as helpers


class Koinly():
    """
    Class for exporting data in Koinly format
    """
    def __init__(self):
        self.si = io.StringIO()
        self.writer = csv.writer(self.si)
        self.graphql = GraphQL()
        self.constants = helpers.Config().constants()

    def download_export(self, address, export_type):

        # Specify the headers for the Koinly import
        header = [
            "Koinly Date", "Amount", "Currency", "Label", "TxHash",
            "Net Worth Amount", "Net Worth Currency", "Description"
        ]

        if export_type == "transactions":

            # Get all the transaction data for this account
            transactions = self.graphql.get_transactions(address)

            # Determine if the account is in the genesis ledger
            genesis_ledger = self.graphql.get_genesis_info(address)

            if not genesis_ledger["stake"]:
                burn_fee = True
            else:
                burn_fee = False

            # write the header
            self.writer.writerow(header)

            i = 1

            # Loop through all transactions
            for tx in transactions["transactions"]:

                # Is this a withdrawal - if so include the fee and the balance as negative
                if tx["from"] == address:
                    amount = -(tx["amount"] + tx["fee"])
                else:  # This is a deposit transaction
                    amount = tx["amount"]

                    # Might be a delegation or memo transaction but this is not of interest if amount is 0
                    if amount == 0:
                        continue

                # Is this a pool payout, if so label as REWARD
                # See labels here https://help.koinly.io/en/articles/3663453-what-are-labels
                if self.constants["pool_payout_keyword"] in helpers.TaxTools(
                ).memo_parser(tx["memo"]):
                    label = "reward"
                else:
                    label = ""

                self.writer.writerow([
                    tx["dateTime"],
                    helpers.TaxTools().mina_format(amount), "MINA", label,
                    tx["hash"],
                    helpers.TaxTools().calculate_net_worth(
                        tx["dateTime"], amount), "USD",
                    helpers.TaxTools().memo_parser(tx["memo"])
                ])

                # After the first tx we may have burnt 1 MINA if the address was not in the Genesis ledger
                if i == 1 and burn_fee == True:
                    self.writer.writerow([
                        transactions["transactions"][0]["dateTime"], -1,
                        "MINA", "", transactions["transactions"][0]["hash"],
                        helpers.TaxTools().calculate_net_worth(
                            tx["dateTime"], 1000000000), "USD", "Ledger Fee"
                    ])

                i += 1

        # Handle the genesis grants
        elif export_type == "genesis":

            self.writer.writerow(header)

            # Did this account have any balances in the Genesis ledger?
            genesis_ledger = self.graphql.get_genesis_info(address)

            # We can hard code in the date of the Genesis ledger and the value of the tokens at that date
            if genesis_ledger["stake"]:

                self.writer.writerow([
                    self.constants["genesis_date"],
                    genesis_ledger["stake"]["balance"], "MINA", "other income",
                    self.constants["genesis_state_hash"],
                    genesis_ledger["stake"]["balance"] *
                    self.constants["pre_trading_value"], "USD",
                    "Genesis Token Grant"
                ])

        # Handle the block production - this should be the coinbase receiver address if used
        elif export_type == "production":

            self.writer.writerow(header)

            # Get all blocks produced by this key
            blocks = self.graphql.get_blocks_produced(address)

            for block in blocks["blocks"]:

                # Include any tx fees and deduct any snark fees
                amount = int(block["transactions"]["coinbase"]) + int(
                    block["txFees"]) - int(block["snarkFees"])

                self.writer.writerow([
                    block["dateTime"],
                    helpers.TaxTools().mina_format(amount), "MINA", "mining",
                    block["stateHash"],
                    helpers.TaxTools().calculate_net_worth(
                        parse(block["dateTime"]), amount), "USD", block["blockHeight"]
                ])

        # Export SNARK work
        elif export_type == "snarks":

            self.writer.writerow(header)

            # Get all snark work produced by this key
            snarks = self.graphql.get_snarks_sold(address)

            for snark in snarks["snarks"]:

                self.writer.writerow([
                    snark["dateTime"],
                    helpers.TaxTools().mina_format(snark["fee"]), "MINA",
                    "mining", '',
                    helpers.TaxTools().calculate_net_worth(
                        parse(snark["dateTime"]),
                        snark["fee"]), "USD", snark["blockHeight"]
                ])

        return (self.si.getvalue())
