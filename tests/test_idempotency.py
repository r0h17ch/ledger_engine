import pytest
from uuid import uuid4

from ledger_engine.database import get_connection
from ledger_engine.posting import deposit


def create_account():
    account_id = str(uuid4())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (id, name, currency)
                VALUES (%s, 'Idempotency Test', 'INR')
                """,
                (account_id,)
            )

    return account_id


def test_duplicate_request_is_processed_once():
    account_id = create_account()
    key = str(uuid4())

    first_transaction = deposit(account_id, 50000, key)
    second_transaction = deposit(account_id, 50000, key)

    assert first_transaction == second_transaction

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (account_id,)
            )
            balance = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM transactions
                WHERE idempotency_key = %s
                """,
                (key,)
            )
            transaction_count = cur.fetchone()[0]

    assert balance == 50000
    assert transaction_count == 1


def test_same_key_with_different_amount_is_rejected():
    account_id = create_account()
    key = str(uuid4())

    deposit(account_id, 50000, key)

    with pytest.raises(ValueError, match="different request"):
        deposit(account_id, 90000, key)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (account_id,)
            )
            balance = cur.fetchone()[0]

    assert balance == 50000
