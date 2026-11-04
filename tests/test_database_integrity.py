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
                SELECT id
                FROM ledger_entries
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
                    UPDATE ledger_entries
                    SET debit = debit + 1
                    WHERE id = %s
                    """,
                    (entry[0],)
                )
