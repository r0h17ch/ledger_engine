from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from ledger_engine.engine import LedgerEngine

def test_reproduce_race_contition():

    bank = LedgerEngine()
    bank.create_account("alice")
    bank.deposit("alice", 1000)

    barrier = Barrier(2)
    org_get_balance = bank.get_balance

    def sync_get_balance(account_id):
        balance = org_get_balance(account_id)
        if account_id == "alice":
            barrier.wait()
        return balance
    
    bank.get_balance = sync_get_balance

    def withdraw():
        bank.withdraw("alice", 800)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(withdraw),
            executor.submit(withdraw)
        ]
        for future in futures:
            future.result()

    bank.get_balance = org_get_balance

    print("Alice's final balance:", bank.get_balance("alice"))

    assert bank.get_balance("alice") == -600