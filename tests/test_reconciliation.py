from uuid import uuid4

from ledger_engine.database import get_connection
from ledger_engine.posting import deposit
from ledger_engine.reconciliation import (
    reconcile_accounts,
    reconciliation_summary
)


def create_account():
    account_id = str(uuid4())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (id, name, currency)
                VALUES (%s, 'Reconciliation Test', 'INR')
                """,
                (account_id,)
            )

    return account_id


def test_account_reconciles_after_deposit():
    account_id = create_account()

    deposit(account_id, 100000, str(uuid4()))

    results = reconcile_accounts()

    account = next(
        item for item in results
        if item["account_id"] == account_id
    )

    assert account["stored_balance"] == 100000
    assert account["ledger_balance"] == 100000
    assert account["difference"] == 0
    assert account["is_balanced"] is True


def test_reconciliation_detects_balance_mismatch():
    account_id = create_account()

    deposit(account_id, 100000, str(uuid4()))

    # Simulate corruption in the balance projection.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE accounts
                SET balance = balance + 5000
                WHERE id = %s
                """,
                (account_id,)
            )

    results = reconcile_accounts()

    account = next(
        item for item in results
        if item["account_id"] == account_id
    )

    assert account["stored_balance"] == 105000
    assert account["ledger_balance"] == 100000
    assert account["difference"] == 5000
    assert account["is_balanced"] is False


def test_reconciliation_summary():
    summary = reconciliation_summary()

    assert summary["total_accounts"] >= 1
    assert summary["mismatched_accounts"] >= 1
    assert summary["is_reconciled"] is False
