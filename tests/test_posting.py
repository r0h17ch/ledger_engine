from ledger_engine.database import get_connection
from ledger_engine.posting import deposit

def test_deposit():
    account_id = "00000000-0000-0000-0000-000000000002"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (id, name, currency)
                VALUES (%s, 'Alice', 'INR')
                ON CONFLICT (id) DO NOTHING
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