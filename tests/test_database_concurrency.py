from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from ledger_engine.database import get_connection
from ledger_engine.posting import deposit, withdraw


def create_account():
    account_id = str(uuid4())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (id, name, currency)
                VALUES (%s, 'Concurrency Test', 'INR')
                """,
                (account_id,)
            )

    return account_id


def test_concurrent_withdrawals():
    account_id = create_account()

    # Deposit ₹1,000 = 100000 paise.
    deposit(account_id, 100000)

    def attempt_withdrawal():
        try:
            withdraw(account_id, 80000)
            return "success"
        except ValueError:
            return "failed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(attempt_withdrawal),
            executor.submit(attempt_withdrawal)
        ]

        results = [future.result() for future in futures]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (account_id,)
            )
            balance = cur.fetchone()[0]

    print("Results:", results)
    print("Final balance:", balance)

    assert results.count("success") == 1
    assert results.count("failed") == 1
    assert balance == 20000
