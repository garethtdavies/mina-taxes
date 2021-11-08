from google.cloud import bigquery


class BigQuery():
    def __init__(self):
        """Define the BigQuery connection"""
        self.client = bigquery.Client()

    def get_transactions(self, address, start_date, end_date):

        query = ("""
        SELECT tx.amount,
            tx.fee,
            tx.`from`,
            tx.`to`,
            tx.`hash`,
            tx.id,
            tx.isdelegation,
            tx.memo,
            tx.nonce,
            tx.`datetime`,
            tx.blockstatehash,
            tx.blockheight,
            tx.`kind`
        FROM (
                SELECT t.amount,
                        t.fee,
                        t.`from`,
                        t.`to`,
                        t.`hash`,
                        t.id,
                        t.isdelegation,
                        t.memo,
                        t.nonce,
                        t.`datetime`,
                        t.blockstatehash,
                        t.blockheight,
                        t.`kind`
                FROM minaexplorer.archive.transactions as t
                WHERE `to` = '{0}'
                AND canonical = true
                AND failurereason is Null
                AND datetime >= '{1}'
                AND datetime < '{2}'
                UNION ALL
                SELECT t.amount,
                        t.fee,
                        t.`from`,
                        t.`to`,
                        t.`hash`,
                        t.id,
                        t.isdelegation,
                        t.memo,
                        t.nonce,
                        t.`datetime`,
                        t.blockstatehash,
                        t.blockheight,
                        t.`kind`
                FROM minaexplorer.archive.transactions as t
                WHERE `from` = '{0}'
                AND canonical = true
                AND failurereason is Null
                AND datetime >= '{1}'
                AND datetime < '{2}'
            ) tx
        ORDER BY datetime ASC,
                nonce ASC
        """.format(address, start_date, end_date))

        query_job = self.client.query(query)

        return {"transactions": query_job.result()}
