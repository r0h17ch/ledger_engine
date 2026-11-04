import pytest
import psycopg
from uuid import uuid4

from ledger_engine.database import get_connection
from ledger_engine.posting import deposit, withdraw, transfer, SYSTEM_ACCOUNT_ID


def create_test_account(name):
    account_id = str(uuid4())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (id, name, currency)
                VALUES (%s, %s, 'INR')
                """,
                (account_id, name)
            )

    return account_id


def test_deposit():
    account_id = create_test_account("Alice")

    deposit(account_id, 100000)

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
                FROM ledger_entries
                WHERE account_id = %s
                """,
                (account_id,)
            )
            entry_count = cur.fetchone()[0]

    assert balance == 100000
    assert entry_count == 1


def test_deposit_rolls_back_on_ledger_failure():
    account_id = create_test_account("Rollback Test")

    # Capture the initial state.
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

    # Inject a failure before ledger entry insertion.
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
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DROP TRIGGER IF EXISTS test_ledger_failure
                    ON ledger_entries;
                """)

                cur.execute("""
                    DROP FUNCTION IF EXISTS simulate_ledger_failure();
                """)

    # Verify rollback.
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


def test_withdraw():
    account_id = create_test_account("Withdrawal Test")

    deposit(account_id, 100000)
    withdraw(account_id, 30000)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (account_id,)
            )
            balance = cur.fetchone()[0]

    assert balance == 70000


def test_transfer():
    alice = create_test_account("Transfer Alice")
    bob = create_test_account("Transfer Bob")

    deposit(alice, 100000)
    transfer(alice, bob, 40000)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (alice,)
            )
            alice_balance = cur.fetchone()[0]

            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (bob,)
            )
            bob_balance = cur.fetchone()[0]

    assert alice_balance == 60000
    assert bob_balance == 40000


def test_withdrawal_cannot_overdraw():
    account_id = create_test_account("Overdraft Test")

    deposit(account_id, 10000)

    with pytest.raises(ValueError):
        withdraw(account_id, 20000)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance FROM accounts WHERE id = %s",
                (account_id,)
            )
            balance = cur.fetchone()[0]

    assert balance == 10000


def test_transfer_to_same_account_rejected():
    account_id = create_test_account("Same Account Test")

    deposit(account_id, 10000)

    with pytest.raises(ValueError):
        transfer(account_id, account_id, 1000)
