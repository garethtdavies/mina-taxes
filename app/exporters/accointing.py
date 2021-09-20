import io
import csv
from app.graphql import GraphQL
import app.helpers as helpers
from dateutil import parser


class Accointing():
    """
    Class for exporting data in Accointing format
    """
    def __init__(self):
        self.si = io.StringIO()
        self.writer = csv.writer(self.si)
        self.graphql = GraphQL()
        self.constants = helpers.Config().constants()

    def download_export(self, address, export_type):

        # Specify the headers for the Accointing import
        header = [
            "transactionType", "date", "inBuyAmount", "inBuyAsset",
            "outSellAmount", "outSellAsset", "feeAmount (optional)",
            "feeAsset (optional)", "classification (optional)",
            "operationId (optional)"
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
                    tx_type = "withdraw"
                    amount = tx["amount"]
                    fee = tx["fee"]
                else:  # This is a deposit transaction
                    tx_type = "deposit"
                    amount = tx["amount"]

                    # Might be a delegation or memo transaction but this is not of interest if amount is 0
                    if amount == 0:
                        continue

                # Is this a pool payout, if so label as REWARD
                if self.constants["pool_payout_keyword"] in helpers.TaxTools(
                ).memo_parser(tx["memo"]):
                    label = "staked"
                else:
                    label = ""

                # format the date for accointing
                format_date = parser.parse(tx["dateTime"])

                # Define the basic structure and we'll add specifics to it later
                data = [
                    tx_type,
                    format_date.strftime("%m/%d/%Y %H:%M:%S"),
                    label,
                    tx["hash"],
                ]

                if tx_type == "deposit":
                    data.insert(2, helpers.TaxTools().mina_format(amount))
                    data.insert(3, "MINA"),
                    data.insert(4, ""),
                    data.insert(5, ""),
                    data.insert(6, "")
                    data.insert(7, "")
                elif tx_type == "withdraw":
                    data.insert(2, "")
                    data.insert(3, ""),
                    data.insert(4, helpers.TaxTools().mina_format(amount)),
                    data.insert(5, "MINA"),
                    data.insert(6, helpers.TaxTools().mina_format(fee))
                    data.insert(7, "MINA")

                self.writer.writerow(data)

                # After the first tx we may have burnt 1 MINA if the address was not in the Genesis ledger
                if i == 1 and burn_fee == True:
                    self.writer.writerow([
                        "withdraw",
                        format_date.strftime("%m/%d/%Y %H:%M:%S"),
                        "",
                        "",
                        helpers.TaxTools().mina_format(1000000000),
                        "MINA",
                        "",
                        "",
                        "",
                        tx["hash"],
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
                        block["dateTime"], amount), "USD", block["blockHeight"]
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
                        snark["dateTime"],
                        snark["fee"]), "USD", snark["blockHeight"]
                ])

        return (self.si.getvalue())
