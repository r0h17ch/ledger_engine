import pytest
import psycopg

from ledger_engine.database import get_connection
from ledger_engine.posting import deposit, SYSTEM_ACCOUNT_ID


def test_deposit_rolls_back_on_ledger_failure():
    account_id = "00000000-0000-0000-0000-000000000003"

    # Create a fresh account.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (id, name, currency)
                VALUES (%s, 'Rollback Test', 'INR')
                """,
                (account_id,)
            )

    # Record balances before the operation.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (account_id,)
            )
            account_before = cur.fetchone()[0]

            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (SYSTEM_ACCOUNT_ID,)
            )
            system_before = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM transactions")
            transactions_before = cur.fetchone()[0]

    # Inject a database failure during ledger insertion.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE OR REPLACE FUNCTION simulate_ledger_failure()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'Simulated ledger insertion failure';
                END;
                $$ LANGUAGE plpgsql;
            """)

            cur.execute("""
                CREATE TRIGGER test_ledger_failure
                BEFORE INSERT ON ledger_entries
                FOR EACH ROW
                EXECUTE FUNCTION simulate_ledger_failure();
            """)

    try:
        with pytest.raises(psycopg.errors.RaiseException):
            deposit(account_id, 50000)

    finally:
        # Remove the injected failure.
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DROP TRIGGER IF EXISTS test_ledger_failure
                    ON ledger_entries;
                """)
                cur.execute("""
                    DROP FUNCTION IF EXISTS simulate_ledger_failure();
                """)

    # Verify that everything was rolled back.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (account_id,)
            )
            account_after = cur.fetchone()[0]

            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (SYSTEM_ACCOUNT_ID,)
            )
            system_after = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM transactions")
            transactions_after = cur.fetchone()[0]

    assert account_after == account_before
    assert system_after == system_before
    assert transactions_after == transactions_before

    print("Account balance unchanged:", account_after)
    print("System balance unchanged:", system_after)
    print("Transaction count unchanged:", transactions_after)


def test_deposit():
    account_id = "00000000-0000-0000-0000-000000000002"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (id, name, currency)
                VALUES (%s, 'Alice', 'INR')
                ON CONFLICT (id) DO UPDATE SET balance = 0
                """,
                (account_id,)
            )

            cur.execute(
                """
                DELETE FROM ledger_entries WHERE account_id = %s
                """,
                (account_id,)
            )

    deposit(account_id, 100000)

    with get_connection() as conn: 
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT balance FROM accounts WHERE id = %s
                """,
                (account_id,)
            )
            balance = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM ledger_entries
                WHERE account_id = %s
                """,
                (account_id,)
            )
            entry_count = cur.fetchone()[0]

    assert balance == 100000
    assert entry_count == 1