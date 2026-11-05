from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from ledger_engine.engine import LedgerEngine

def test_concurrent_withdrawals_cannot_overdraw():

    bank = LedgerEngine()
    bank.create_account("alice")
    bank.deposit("alice", 1000)

    def withdraw():
        try:
            bank.withdraw("alice", 800)
            return "success"
        except ValueError:
            return "failed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(withdraw),
            executor.submit(withdraw)
        ]

    results = [future.result() for future in futures]

    assert results.count("success") == 1
    assert results.count("failed") == 1
    assert bank.get_balance("alice") == 200

    print("Withdrawal results:", results)
    print("Alice's final balance:", bank.get_balance("alice"))