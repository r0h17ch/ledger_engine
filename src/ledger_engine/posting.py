import psycopg
from uuid import uuid4

from ledger_engine.database import get_connection


SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000001"


def post_transaction(entries, description):
    """
    Post a balanced transaction atomically.

    Each entry:
    {
        "account_id": "...",
        "debit": 1000,
        "credit": 0
    }
    """

    if not isinstance(entries, list) or len(entries) < 2:
        raise ValueError("At least two entries are required")

    account_ids = []

    total_debit = 0
    total_credit = 0

    for entry in entries:
        debit = entry["debit"]
        credit = entry["credit"]
        account_id = entry["account_id"]

        if not isinstance(debit, int) or isinstance(debit, bool):
            raise ValueError("Debit must be an integer")

        if not isinstance(credit, int) or isinstance(credit, bool):
            raise ValueError("Credit must be an integer")

        if debit < 0 or credit < 0:
            raise ValueError("Amounts cannot be negative")

        if (debit > 0) == (credit > 0):
            raise ValueError("Exactly one side must be positive")

        if not account_id:
            raise ValueError("Account ID is required")

        account_ids.append(account_id)
        total_debit += debit
        total_credit += credit

    if len(set(account_ids)) != len(account_ids):
        raise ValueError("Duplicate account entries are not allowed")

    if total_debit != total_credit:
        raise ValueError("Transaction is not balanced")

    transaction_id = str(uuid4())

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:

                # Lock accounts in deterministic order.
                sorted_ids = sorted(account_ids)

                cur.execute(
                    """
                    SELECT id
                    FROM accounts
                    WHERE id = ANY(%s::uuid[])
                    ORDER BY id
                    FOR UPDATE
                    """,
                    (sorted_ids,)
                )

                locked_accounts = cur.fetchall()

                if len(locked_accounts) != len(set(account_ids)):
                    raise ValueError("One or more accounts do not exist")

                # Create transaction.
                cur.execute(
                    """
                    INSERT INTO transactions
                        (id, description, currency)
                    VALUES (%s, %s, 'INR')
                    """,
                    (transaction_id, description)
                )

                # Update account balance projections.
                for entry in entries:
                    cur.execute(
                        """
                        UPDATE accounts
                        SET balance = balance + %s - %s
                        WHERE id = %s
                          AND currency = 'INR'
                        """,
                        (
                            entry["credit"],
                            entry["debit"],
                            entry["account_id"]
                        )
                    )

                    if cur.rowcount != 1:
                        raise ValueError("Account currency mismatch")

                # Insert immutable ledger entries.
                cur.executemany(
                    """
                    INSERT INTO ledger_entries
                        (transaction_id, account_id, currency, debit, credit)
                    VALUES (%s, %s, 'INR', %s, %s)
                    """,
                    [
                        (
                            transaction_id,
                            entry["account_id"],
                            entry["debit"],
                            entry["credit"]
                        )
                        for entry in entries
                    ]
                )

    except psycopg.errors.CheckViolation as exc:
        raise ValueError("Insufficient funds or database constraint violated") from exc

    return transaction_id


def deposit(account_id: str, amount: int):
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise ValueError("Amount must be an integer")

    if amount <= 0:
        raise ValueError("Amount must be positive")

    return post_transaction(
        [
            {
                "account_id": SYSTEM_ACCOUNT_ID,
                "debit": amount,
                "credit": 0
            },
            {
                "account_id": account_id,
                "debit": 0,
                "credit": amount
            }
        ],
        "Account deposit"
    )


def withdraw(account_id: str, amount: int):
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise ValueError("Amount must be an integer")

    if amount <= 0:
        raise ValueError("Amount must be positive")

    return post_transaction(
        [
            {
                "account_id": account_id,
                "debit": amount,
                "credit": 0
            },
            {
                "account_id": SYSTEM_ACCOUNT_ID,
                "debit": 0,
                "credit": amount
            }
        ],
        "Account withdrawal"
    )


def transfer(source_account_id: str, destination_account_id: str, amount: int):
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise ValueError("Amount must be an integer")

    if amount <= 0:
        raise ValueError("Amount must be positive")

    if source_account_id == destination_account_id:
        raise ValueError("Cannot transfer to the same account")

    return post_transaction(
        [
            {
                "account_id": source_account_id,
                "debit": amount,
                "credit": 0
            },
            {
                "account_id": destination_account_id,
                "debit": 0,
                "credit": amount
            }
        ],
        "Account transfer"
    )
