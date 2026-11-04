from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
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
                VALUES (%s, 'Concurrent Idempotency', 'INR')
                """,
                (account_id,)
            )

    return account_id


def test_concurrent_duplicate_requests():
    account_id = create_account()
    idempotency_key = str(uuid4())

    barrier = Barrier(2)

    def make_request():
        barrier.wait()

        return deposit(
            account_id,
            50000,
            idempotency_key
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(make_request),
            executor.submit(make_request)
        ]

        transaction_ids = [
            future.result()
            for future in futures
        ]

    assert transaction_ids[0] == transaction_ids[1]

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
                (idempotency_key,)
            )
            transaction_count = cur.fetchone()[0]

    print("Transaction IDs:", transaction_ids)
    print("Final balance:", balance)
    print("Transactions created:", transaction_count)

    assert balance == 50000
    assert transaction_count == 1
