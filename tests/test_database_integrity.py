import pytest
import psycopg
from uuid import uuid4

from ledger_engine.database import get_connection


def test_database_rejects_unbalanced_transaction():
    transaction_id = str(uuid4())

    with pytest.raises(psycopg.errors.RaiseException):
        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO transactions (id, description, currency)
                    VALUES (%s, 'Invalid transaction', 'INR')
                    """,
                    (transaction_id,)
                )

                # Only one debit entry: deliberately unbalanced.
                cur.execute(
                    """
                    INSERT INTO ledger_entries
                        (transaction_id, account_id, currency, debit, credit)
                    VALUES (
                        %s,
                        '00000000-0000-0000-0000-000000000001',
                        'INR',
                        1000,
                        0
                    )
                    """,
                    (transaction_id,)
                )


def test_posted_ledger_entry_cannot_be_modified():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT le.id
                FROM ledger_entries le
                JOIN transactions t ON t.id = le.transaction_id
                WHERE t.posted_at IS NOT NULL
                ORDER BY le.id
                LIMIT 1;
                """
            )
            entry = cur.fetchone()

    assert entry is not None

    with pytest.raises(psycopg.errors.RaiseException):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE ledger_entries
                    SET debit = debit + 1
                    WHERE id = %s
                    """,
                    (entry[0],)
                )


def test_posted_ledger_entry_cannot_be_deleted():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT le.id
                FROM ledger_entries le
                JOIN transactions t ON t.id = le.transaction_id
                WHERE t.posted_at IS NOT NULL
                ORDER BY le.id
                LIMIT 1
                """
            )
            entry = cur.fetchone()

    assert entry is not None

    with pytest.raises(psycopg.errors.RaiseException):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM ledger_entries
                    WHERE id = %s
                    """,
                    (entry[0],)
                )


def test_entry_cannot_be_moved_into_posted_transaction():
    source_transaction_id = str(uuid4())
    target_transaction_id = str(uuid4())
    source_account_id = str(uuid4())
    target_account_id = str(uuid4())

    with pytest.raises(psycopg.errors.RaiseException):
        with get_connection() as conn:
            with conn.cursor() as cur:

                # Create two accounts.
                cur.execute(
                    """
                    INSERT INTO accounts (id, name, currency)
                    VALUES
                        (%s, 'Source Test Account', 'INR'),
                        (%s, 'Target Test Account', 'INR')
                    """,
                    (source_account_id, target_account_id)
                )

                # Create both transactions as drafts.
                cur.execute(
                    """
                    INSERT INTO transactions (id, description, currency)
                    VALUES
                        (%s, 'Source transaction', 'INR'),
                        (%s, 'Target transaction', 'INR')
                    """,
                    (source_transaction_id, target_transaction_id)
                )

                # Add an entry to the source transaction.
                cur.execute(
                    """
                    INSERT INTO ledger_entries
                        (transaction_id, account_id, currency, debit, credit)
                    VALUES (%s, %s, 'INR', 1000, 0)
                    """,
                    (source_transaction_id, source_account_id)
                )

                # Add two balanced entries to the target.
                cur.execute(
                    """
                    INSERT INTO ledger_entries
                        (transaction_id, account_id, currency, debit, credit)
                    VALUES
                        (%s, %s, 'INR', 1000, 0),
                        (%s, %s, 'INR', 0, 1000)
                    """,
                    (
                        target_transaction_id, source_account_id,
                        target_transaction_id, target_account_id
                    )
                )

                # Post the target transaction.
                cur.execute(
                    """
                    UPDATE transactions
                    SET posted_at = NOW()
                    WHERE id = %s
                    """,
                    (target_transaction_id,)
                )

                # Attempt to move the source entry into the posted target.
                # The immutability trigger should reject this immediately.
                cur.execute(
                    """
                    UPDATE ledger_entries
                    SET transaction_id = %s
                    WHERE transaction_id = %s
                    """,
                    (target_transaction_id, source_transaction_id)
                )