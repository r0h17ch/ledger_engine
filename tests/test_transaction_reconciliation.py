from uuid import uuid4

from ledger_engine.posting import deposit
from ledger_engine.reconciliation import reconcile_transactions
from ledger_engine.database import get_connection


def test_valid_transaction_is_not_flagged():
    account_id = str(uuid4())

    # Create a test account using your existing helper.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into accounts (id, name, currency)
                values (%s, 'transaction rec check', 'INR')
                """,
                (account_id,)
            )

    transaction_id = deposit(
        account_id,
        50000,
        str(uuid4())
    )

    issues = reconcile_transactions()

    flagged_ids = {
        issue["transaction_id"]
        for issue in issues
    }

    assert transaction_id not in flagged_ids