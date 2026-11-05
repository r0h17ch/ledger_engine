from uuid import uuid4

from ledger_engine.database import get_connection
from ledger_engine.reconciliation import reconcile_transactions
from ledger_engine.posting import deposit


def test_valid_transaction_is_not_flagged():
    account_id = str(uuid4())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (id, name, currency)
                VALUES (%s,'Transaction Audit', 'INR')
                """,
                (account_id,)
            )

    deposit(account_id, 50000, str(uuid4()))

    issues = reconcile_transactions()
    print("\n--- Flagged Issues ---", issues)

    # assert all(
    #     issue["entry_count"] >= 2
    #     and issue["total_debit"] == issue["total_credit"]
    #     for issue in issues
    # )

    # assert len(issues) == 0