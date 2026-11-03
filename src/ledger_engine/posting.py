from uuid import uuid4
from ledger_engine.database import get_connection

SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000001"

def deposit(account_id: str, amount: int):
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise ValueError("Amount must be an integer")

    if amount <= 0:
        raise ValueError("amount must be positive")

    transaction_id = str(uuid4())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (id, description, currency)
                VALUES (%s, %s, %s)
                """,
                (transaction_id, "Account deposit", "INR")
            )

            # Lock both accounts in deterministic order
            account_ids = sorted([account_id, SYSTEM_ACCOUNT_ID])
            cur.execute(
                """
                SELECT id 
                FROM accounts
                WHERE id = ANY(%s::uuid[])
                ORDER BY id
                FOR UPDATE
                """,
                (account_ids,)
            )

            locked_accounts = cur.fetchall()

            if len(locked_accounts) != 2:
                raise ValueError("Account does not exist")

            # Update account balances
            cur.execute(
                """
                UPDATE accounts
                SET balance = balance + %s
                WHERE id = %s
                """,
                (amount, account_id)
            )

            cur.execute(
                """
                UPDATE accounts
                SET balance = balance - %s
                WHERE id = %s
                """,
                (amount, SYSTEM_ACCOUNT_ID)
            )

            # Insert immutable ledger entries
            cur.execute(
                """
                INSERT INTO ledger_entries
                    (transaction_id, account_id, currency, debit, credit)
                VALUES
                    (%s, %s, 'INR', %s, 0),
                    (%s, %s, 'INR', 0, %s)
                """,
                (
                    transaction_id,
                    SYSTEM_ACCOUNT_ID,
                    amount,
                    transaction_id,
                    account_id,
                    amount
                )
            )
    return transaction_id