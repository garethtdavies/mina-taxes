from sqlalchemy import create_engine, Column, BigInteger, Integer, String, Boolean, Index, TIMESTAMP
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy import text
import os
from datetime import datetime

Base = declarative_base()

class StakingPayouts(Base):
    __tablename__ = "staking_payouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_key = Column(String(255), nullable=False)
    payout = Column(BigInteger, nullable=False)
    block_height = Column(Integer, nullable=False)
    epoch = Column(Integer, nullable=False)
    ledger_hash = Column(String(255), nullable=False)
    date_time = Column(TIMESTAMP(6), nullable=False)
    payment_hash = Column(String(255), nullable=True)
    nonce = Column(Integer, nullable=True)

    __table_args__ = (
        Index('idx_staking_payouts_public_key', 'public_key'),
        Index('idx_staking_payouts_epoch_ledger', 'epoch', 'ledger_hash'),
        Index('idx_staking_payouts_pending', 'payment_hash', 'public_key'),
        Index('idx_staking_payouts_payment_hash', 'payment_hash'),
        Index('idx_staking_payouts_unique', 'block_height', 'public_key', unique=True),
    )


class PostgreSQL:
    def __init__(self):
        """Initialize PostgreSQL connection"""
        db_url = os.getenv('POSTGRES_URI')
        if not db_url:
            raise ValueError("POSTGRES_URI environment variable not set")
        
        self.engine = create_engine(db_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    # ================================================================
    # Koinly Export Methods (replaces GraphQL queries)
    # ================================================================

    def get_first_transaction_received(self, address):
        """
        Determines the first transaction received by an address
        Replaces GraphQL: get_first_transaction_received
        
        Args:
            address: The public key address
            
        Returns:
            Dictionary with 'transactions' key containing list of transaction dicts
        """
        query = text("""
            SELECT 
                date_time as "dateTime",
                "from",
                "to",
                amount,
                hash,
                kind,
                block_height as "blockHeight",
                block_state_hash as "stateHash"
            FROM transactions
            WHERE "to" = :address
                AND canonical = true
            ORDER BY date_time ASC
            LIMIT 1
        """)
        
        result = self.session.execute(query, {"address": address}).fetchone()
        
        if result:
            return {
                "transactions": [{
                    "dateTime": result.dateTime.isoformat() + "Z" if result.dateTime else None,
                    "from": result[1],  # "from" is a reserved word
                    "to": result[2],
                    "amount": result.amount,
                    "hash": result.hash,
                    "kind": result.kind,
                    "block": {
                        "blockHeight": result.blockHeight,
                        "stateHash": result.stateHash
                    }
                }]
            }
        return {"transactions": []}

    def get_transactions(self, address, start_date, end_date):
        """
        Get all transaction data for a given address within a date range
        Replaces GraphQL: get_transactions
        
        Args:
            address: The public key address
            start_date: Start date (ISO format string)
            end_date: End date (ISO format string)
            
        Returns:
            Dictionary with 'transactions' key containing list of transaction dicts
        """
        query = text("""
            SELECT 
                fee,
                "from",
                "to",
                nonce,
                amount,
                memo,
                hash,
                kind,
                date_time as "dateTime",
                block_height as "blockHeight",
                block_state_hash as "stateHash"
            FROM transactions
            WHERE canonical = true
                AND date_time >= :start_date
                AND date_time < :end_date
                AND ("to" = :address OR "from" = :address)
            ORDER BY date_time ASC
        """)
        
        results = self.session.execute(query, {
            "address": address,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        transactions = []
        for row in results:
            transactions.append({
                "fee": row.fee or 0,
                "from": row[1],  # "from" is a reserved word
                "to": row[2],
                "nonce": row.nonce,
                "amount": row.amount or 0,
                "memo": row.memo,
                "hash": row.hash,
                "kind": row.kind,
                "dateTime": row.dateTime.isoformat() + "Z" if row.dateTime else None,
                "block": {
                    "blockHeight": row.blockHeight,
                    "stateHash": row.stateHash
                }
            })
        
        return {"transactions": transactions}
    
    def get_zkapp_transactions(self, address, start_date, end_date):
        """
        Get zkApp transactions involving an address
        
        Returns transactions where address is:
        - The fee payer (always includes fee, even on failed transactions)
        - In an account update with MINA balance change (successful only)
        """
        MINA_TOKEN = "wSHV2S4qX9jFsLjQo8r1BsMLH2ZRKsZx6EJd1sbozGPieEC4Jf"
        
        query = text("""
            SELECT 
                z.hash,
                z.date_time as "dateTime",
                z.block_height as "blockHeight",
                z.block_state_hash as "stateHash",
                z.zkapp_command as "zkappCommand"
            FROM zkapps z
            WHERE z.canonical = true
                AND z.date_time >= :start_date
                AND z.date_time < :end_date
                AND (
                    z.zkapp_command->'feePayer'->'body'->>'publicKey' = :address
                    OR EXISTS (
                        SELECT 1 FROM jsonb_array_elements(z.zkapp_command->'accountUpdates') AS au
                        WHERE au->'body'->>'publicKey' = :address
                        AND au->'body'->>'tokenId' = :mina_token
                    )
                )
            ORDER BY z.date_time ASC
        """)
        
        results = self.session.execute(query, {
            "address": address,
            "start_date": start_date,
            "end_date": end_date,
            "mina_token": MINA_TOKEN
        }).fetchall()
        
        transactions = []
        
        for row in results:
            zkapp_cmd = row.zkappCommand or {}
            fee_payer_body = zkapp_cmd.get("feePayer", {}).get("body", {})
            fee_payer_pk = fee_payer_body.get("publicKey")
            fee = int(fee_payer_body.get("fee", 0))
            memo = zkapp_cmd.get("memo", "")
            
            # Check if transaction failed
            failure_reason = zkapp_cmd.get("failureReason")
            is_failed = failure_reason is not None and failure_reason != ""
            
            is_fee_payer = fee_payer_pk == address
            
            if is_fee_payer:
                # Sum all MINA balance changes for fee payer in account updates
                total_balance_change = 0
                
                if not is_failed:
                    for au in zkapp_cmd.get("accountUpdates", []):
                        body = au.get("body", {})
                        if body.get("publicKey") == address and body.get("tokenId") == MINA_TOKEN:
                            bc = body.get("balanceChange", {})
                            magnitude = int(bc.get("magnitude", 0))
                            sgn = bc.get("sgn", "Positive")
                            if sgn == "Negative":
                                total_balance_change -= magnitude
                            else:
                                total_balance_change += magnitude
                
                # Withdrawal: amount includes fee (matches regular tx behavior)
                # amount = -(outgoing_balance + fee)
                if total_balance_change <= 0:
                    amount = total_balance_change - fee  # e.g., -1000000000 - 100000000
                    transactions.append({
                        "dateTime": row.dateTime.isoformat() + "Z" if row.dateTime else None,
                        "hash": row.hash,
                        "blockHeight": row.blockHeight,
                        "stateHash": row.stateHash,
                        "amount": amount,
                        "fee": fee,
                        "from": address,
                        "to": "",
                        "memo": memo,
                        "type": "withdrawal",
                        "failed": is_failed
                    })
                else:
                    # Rare: fee payer receives MINA, net it against fee
                    net_amount = total_balance_change - fee
                    transactions.append({
                        "dateTime": row.dateTime.isoformat() + "Z" if row.dateTime else None,
                        "hash": row.hash,
                        "blockHeight": row.blockHeight,
                        "stateHash": row.stateHash,
                        "amount": net_amount,
                        "fee": fee,
                        "from": "" if net_amount > 0 else address,
                        "to": address if net_amount > 0 else "",
                        "memo": memo,
                        "type": "deposit" if net_amount > 0 else "withdrawal",
                        "failed": is_failed
                    })
            
            # Non-fee-payer with MINA balance changes (only if successful)
            elif not is_failed:
                for au in zkapp_cmd.get("accountUpdates", []):
                    body = au.get("body", {})
                    if body.get("publicKey") == address and body.get("tokenId") == MINA_TOKEN:
                        bc = body.get("balanceChange", {})
                        magnitude = int(bc.get("magnitude", 0))
                        sgn = bc.get("sgn", "Positive")
                        
                        if magnitude > 0:
                            if sgn == "Positive":
                                transactions.append({
                                    "dateTime": row.dateTime.isoformat() + "Z" if row.dateTime else None,
                                    "hash": row.hash,
                                    "blockHeight": row.blockHeight,
                                    "stateHash": row.stateHash,
                                    "amount": magnitude,
                                    "fee": 0,
                                    "from": fee_payer_pk or "",
                                    "to": address,
                                    "memo": memo,
                                    "type": "deposit",
                                    "failed": False
                                })
                            else:
                                transactions.append({
                                    "dateTime": row.dateTime.isoformat() + "Z" if row.dateTime else None,
                                    "hash": row.hash,
                                    "blockHeight": row.blockHeight,
                                    "stateHash": row.stateHash,
                                    "amount": -magnitude,
                                    "fee": 0,
                                    "from": address,
                                    "to": "",
                                    "memo": memo,
                                    "type": "withdrawal",
                                    "failed": False
                                })
        
        return {"zkappTransactions": transactions}

    def get_genesis_info(self, address):
        """
        Determines balance information for an account in the Genesis ledger
        Replaces GraphQL: get_genesis_info
        
        The genesis ledger hash is: jx7buQVWFLsXTtzRgSxbYcT8EYLS8KCZbLrfDcJxMtyy4thw2Ee
        
        Args:
            address: The public key address
            
        Returns:
            Dictionary with 'stake' key containing balance info or None
        """
        genesis_ledger_hash = "jx7buQVWFLsXTtzRgSxbYcT8EYLS8KCZbLrfDcJxMtyy4thw2Ee"
        
        query = text("""
            SELECT 
                ledger_hash as "ledgerHash",
                balance
            FROM staking
            WHERE public_key = :address
                AND ledger_hash = :ledger_hash
            LIMIT 1
        """)
        
        result = self.session.execute(query, {
            "address": address,
            "ledger_hash": genesis_ledger_hash
        }).fetchone()
        
        if result:
            return {
                "stake": {
                    "ledgerHash": result.ledgerHash,
                    "balance": result.balance
                }
            }
        return {"stake": None}

    def get_blocks_produced(self, address, start_date, end_date):
        """
        Get blocks produced by an address (coinbase receiver) within a date range
        Replaces GraphQL: get_blocks_produced
        
        Args:
            address: The coinbase receiver public key
            start_date: Start date (ISO format string)
            end_date: End date (ISO format string)
            
        Returns:
            Dictionary with 'blocks' key containing list of block dicts
        """
        query = text("""
            SELECT 
                date_time as "dateTime",
                state_hash as "stateHash",
                block_height as "blockHeight",
                canonical,
                transactions
            FROM blocks
            WHERE canonical = true
                AND date_time >= :start_date
                AND date_time < :end_date
                AND transactions->'coinbaseReceiverAccount'->>'publicKey' = :address
            ORDER BY date_time ASC
            LIMIT 100000
        """)
        
        results = self.session.execute(query, {
            "address": address,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        blocks = []
        for row in results:
            tx_data = row.transactions or {}
            coinbase_receiver = address
            
            # Calculate fees using fee transfers (includes both user command and zkapp fees)
            fee_transfers = [
                ft for ft in tx_data.get("feeTransfer", [])
                if ft.get("type") == "Fee_transfer"
            ]
            
            fee_transfers_by_coinbase = [
                ft for ft in tx_data.get("feeTransfer", [])
                if ft.get("type") == "Fee_transfer_via_coinbase"
            ]
            
            # Fee transfers to the coinbase receiver (tx fees earned)
            fee_transfer_to_creator = [
                ft for ft in fee_transfers
                if ft.get("recipient") == coinbase_receiver
            ]
            total_fee_transfers_to_creator = sum(
                int(ft.get("fee", 0)) for ft in fee_transfer_to_creator
            )
            
            # Fee transfers via coinbase (paid to snarkers from coinbase)
            fee_transfer_for_coinbase = sum(
                int(ft.get("fee", 0)) for ft in fee_transfers_by_coinbase
            )
            
            # Snark fees = all fee transfers minus those to creator
            total_fee_transfers = sum(int(ft.get("fee", 0)) for ft in fee_transfers)
            snark_fees = total_fee_transfers - total_fee_transfers_to_creator
            
            blocks.append({
                "dateTime": row.dateTime.isoformat() + "Z" if row.dateTime else None,
                "stateHash": row.stateHash,
                "blockHeight": row.blockHeight,
                "canonical": row.canonical,
                "txFees": str(total_fee_transfers_to_creator),
                "snarkFees": str(snark_fees),
                "feeTransferForCoinbase": str(fee_transfer_for_coinbase),
                "transactions": {
                    "coinbase": tx_data.get("coinbase", "0")
                }
            })
        
        return {"blocks": blocks}

    def get_snarks_sold(self, address, start_date, end_date):
        """
        Get snarks sold by a prover within a date range
        Replaces GraphQL: get_snarks_sold
        
        Args:
            address: The prover public key
            start_date: Start date (ISO format string)
            end_date: End date (ISO format string)
            
        Returns:
            Dictionary with 'snarks' key containing list of snark dicts
        """
        query = text("""
            SELECT 
                date_time as "dateTime",
                block_height as "blockHeight",
                fee
            FROM snarks
            WHERE canonical = true
                AND prover = :address
                AND date_time >= :start_date
                AND date_time < :end_date
            ORDER BY date_time ASC
        """)
        
        results = self.session.execute(query, {
            "address": address,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        snarks = []
        for row in results:
            snarks.append({
                "dateTime": row.dateTime.isoformat() + "Z" if row.dateTime else None,
                "blockHeight": row.blockHeight,
                "fee": row.fee or 0
            })
        
        return {"snarks": snarks}

    # ================================================================
    # Staking Payout Methods (existing)
    # ================================================================

    def insert_payouts(self, payouts):
        """
        Insert multiple payout records into the database
        
        Args:
            payouts: List of dictionaries with payout data
            
        Returns:
            Number of records inserted
            
        Raises:
            Exception if insertion fails
        """
        from datetime import datetime
        
        batch_data = []
        
        for payout in payouts:
            # Parse the dateTime field - handle ISO format with 'Z'
            date_time_str = payout.get("dateTime")
            if date_time_str:
                if date_time_str.endswith('Z'):
                    date_time_str = date_time_str[:-1] + '+00:00'
                date_time_obj = datetime.fromisoformat(date_time_str).replace(tzinfo=None)
            else:
                raise ValueError(f"Missing dateTime in payout record")
            
            record = StakingPayouts(
                public_key=payout.get("publicKey"),
                payout=payout.get("payout"),
                block_height=payout.get("blockHeight"),
                epoch=payout.get("epoch"),
                ledger_hash=payout.get("ledgerHash"),
                date_time=date_time_obj,
                payment_hash=None,  # Initially unpaid
                nonce=None  # Initially unpaid
            )
            batch_data.append(record)
        
        try:
            self.session.bulk_save_objects(batch_data)
            self.session.commit()
            return len(batch_data)
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Failed to insert payouts: {e}")

    def get_pending_payments(self, threshold=100000000):
        """
        Get all pending payments aggregated by public key, sorted by total descending
        
        Args:
            threshold: Minimum payout amount in nanomina (default: 100000000 = 0.1 MINA)
            
        Returns:
            List of dictionaries with publicKey and total, sorted largest first
        """
        from sqlalchemy import func
        
        # Query for unpaid payouts, grouped by public_key, sorted by total DESC
        results = self.session.query(
            StakingPayouts.public_key,
            func.sum(StakingPayouts.payout).label('total')
        ).filter(
            StakingPayouts.payment_hash.is_(None)
        ).group_by(
            StakingPayouts.public_key
        ).having(
            func.sum(StakingPayouts.payout) >= threshold
        ).order_by(
            func.sum(StakingPayouts.payout).desc()
        ).all()
        
        # Convert to list of dicts matching the old format
        pending_payments = []
        for row in results:
            pending_payments.append({
                "publicKey": row.public_key,
                "total": row.total
            })
        
        return pending_payments

    def mark_as_paid(self, public_key, payment_hash, nonce, block_heights=None):
        """
        Mark payout records as paid by updating payment_hash and nonce
        
        Args:
            public_key: The public key that was paid
            payment_hash: The transaction hash
            nonce: The transaction nonce
            block_heights: Optional list of specific block_heights to update
                          If None, updates all unpaid records for this public_key
        """
        query = self.session.query(StakingPayouts).filter(
            StakingPayouts.public_key == public_key,
            StakingPayouts.payment_hash.is_(None)
        )
        
        if block_heights:
            query = query.filter(StakingPayouts.block_height.in_(block_heights))
        
        try:
            query.update({
                'payment_hash': payment_hash,
                'nonce': nonce
            }, synchronize_session=False)
            self.session.commit()
            return query.count()
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Failed to mark payouts as paid: {e}")

    def get_unpaid_records(self, public_key=None):
        """
        Get all unpaid payout records, optionally filtered by public_key
        
        Args:
            public_key: Optional filter by specific public key
            
        Returns:
            List of StakingPayouts objects
        """
        query = self.session.query(StakingPayouts).filter(
            StakingPayouts.payment_hash.is_(None)
        )
        
        if public_key:
            query = query.filter(StakingPayouts.public_key == public_key)
        
        return query.all()

    def get_ledger_hash(self, epoch):
        """
        Get the ledger hash for a given epoch from the staking epoch data
        
        Args:
            epoch: The epoch number
            
        Returns:
            String ledger hash or None if not found
        """
        query = text("""
            SELECT 
                protocol_state #>> '{consensusState,stakingEpochData,ledger,hash}' as ledger_hash
            FROM blocks
            WHERE canonical = true
                AND (protocol_state #>> '{consensusState,epoch}')::int = :epoch
                AND block_height >= 359605
            LIMIT 1
        """)
        
        result = self.session.execute(query, {"epoch": epoch}).fetchone()
        return result[0] if result else None

    def get_latest_height(self):
        """
        Get the latest canonical block height
        
        Returns:
            Integer block height or None if not found
        """
        query = text("""
            SELECT MAX(block_height) as block_height
            FROM blocks
            WHERE canonical = true
        """)
        
        result = self.session.execute(query).fetchone()
        return result[0] if result else None

    def get_blocks(self, creator, epoch, block_height_min, block_height_max):
        """
        Get blocks won by a creator in a specific epoch and height range
        
        Args:
            creator: Public key of the block creator
            epoch: Epoch number
            block_height_min: Minimum block height
            block_height_max: Maximum block height
            
        Returns:
            List of block dictionaries with required fields
        """
        query = text("""
            SELECT 
                block_height as "blockHeight",
                canonical,
                creator,
                date_time as "dateTime",
                state_hash as "stateHash",
                state_hash_field as "stateHashField",
                protocol_state,
                transactions
            FROM blocks
            WHERE canonical = true
                AND creator = :creator
                AND (protocol_state #>> '{consensusState,epoch}')::int = :epoch
                AND block_height >= :block_height_min
                AND block_height <= :block_height_max
            ORDER BY date_time DESC
            LIMIT 10000
        """)
        
        results = self.session.execute(query, {
            "creator": creator,
            "epoch": epoch,
            "block_height_min": block_height_min,
            "block_height_max": block_height_max
        }).fetchall()
        
        blocks = []
        for row in results:
            block = {
                "blockHeight": row.blockHeight,
                "canonical": row.canonical,
                "creator": row.creator,
                "dateTime": row.dateTime.isoformat() + "Z" if row.dateTime else None,
                "stateHash": row.stateHash,
                "stateHashField": row.stateHashField,
                "protocolState": row.protocol_state,
                "transactions": row.transactions
            }
            blocks.append(block)
        
        return blocks

    def get_staking_ledger(self, delegate, ledger_hash):
        """
        Get the staking ledger for a delegate and ledger hash
        
        Args:
            delegate: Public key of the delegate
            ledger_hash: The ledger hash for the epoch
            
        Returns:
            List of stake dictionaries matching GraphQL format
        """
        query = text("""
            SELECT 
                public_key,
                balance,
                chain_id as "chainId",
                timing
            FROM staking
            WHERE delegate = :delegate
                AND ledger_hash = :ledger_hash
                AND balance > 0
            ORDER BY balance DESC
            LIMIT 10000
        """)
        
        results = self.session.execute(query, {
            "delegate": delegate,
            "ledger_hash": ledger_hash
        }).fetchall()
        
        stakes = []
        for row in results:
            stake = {
                "public_key": row.public_key,
                "balance": int(row.balance * 1000000000),  # Convert MINA to nanomina
                "chainId": row.chainId,
                "timing": None
            }
            
            # Parse timing if it exists
            if row.timing:
                timing_data = row.timing
                stake["timing"] = {
                    "cliff_amount": timing_data.get("cliff_amount"),
                    "cliff_time": timing_data.get("cliff_time"),
                    "initial_minimum_balance": timing_data.get("initial_minimum_balance"),
                    "timed_epoch_end": timing_data.get("timed_epoch_end"),
                    "timed_in_epoch": timing_data.get("timed_in_epoch"),
                    "timed_weighting": timing_data.get("timed_weighting", 1),
                    "untimed_slot": timing_data.get("untimed_slot"),
                    "vesting_increment": timing_data.get("vesting_increment"),
                    "vesting_period": timing_data.get("vesting_period")
                }
            
            stakes.append(stake)
        
        return stakes

    def close(self):
        """Close the database connection"""
        self.session.close()
