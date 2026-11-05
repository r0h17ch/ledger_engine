from ledger_engine.database import get_connection


def reconcile_accounts():
    """
    Compare stored account balances against
    balances independently calculated from ledger entries.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    a.id,
                    a.name,
                    a.currency,
                    a.balance AS stored_balance,

                    COALESCE(
                        SUM(le.credit - le.debit),
                        0
                    ) AS ledger_balance

                FROM accounts a

                LEFT JOIN ledger_entries le
                    ON le.account_id = a.id

                GROUP BY
                    a.id,
                    a.name,
                    a.currency,
                    a.balance

                ORDER BY a.name
                """
            )

            rows = cur.fetchall()

    results = []

    for row in rows:
        account_id, name, currency, stored, ledger = row

        difference = stored - ledger

        results.append({
            "account_id": str(account_id),
            "name": name,
            "currency": currency,
            "stored_balance": stored,
            "ledger_balance": ledger,
            "difference": difference,
            "is_balanced": difference == 0
        })

    return results


def reconciliation_summary():
    results = reconcile_accounts()

    mismatches = [
        account for account in results
        if not account["is_balanced"]
    ]

    return {
        "total_accounts": len(results),
        "balanced_accounts": len(results) - len(mismatches),
        "mismatched_accounts": len(mismatches),
        "is_reconciled": len(mismatches) == 0,
        "mismatches": mismatches
    }


def reconcile_transactions():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    t.id,
                    t.description,
                    COUNT(le.id) AS entry_count,
                    COALESCE(SUM(le.debit), 0) AS total_debit,
                    COALESCE(SUM(le.credit), 0) AS total_credit

                FROM transactions t

                LEFT JOIN ledger_entries le
                    ON le.transaction_id = t.id

                WHERE t.posted_at IS NOT NULL

                GROUP BY t.id, t.description

                HAVING
                    COUNT(le.id) < 2
                    OR COALESCE(SUM(le.debit), 0)
                        <> COALESCE(SUM(le.credit), 0)

                ORDER BY t.id
                """
            )

            rows = cur.fetchall()

    return [
        {
            "transaction_id" : str(row[0]),
            "description" : row[1],
            "entry_count" : row[2],
            "total_debit" : row[3],
            "total_credit" : row[4]
        }
        for row in rows
    ]


def full_reconciliation():
    account_summary = reconciliation_summary()
    transaction_issues = reconcile_transactions()

    return {
        "accounts" : account_summary,
        "unbalanced_transactions" : len(transaction_issues),
        "transaction_issues" : transaction_issues,
        "is_healty" : (
            account_summary["is_reconciled"]
            and len(transaction_issues) == 0
        )
    }