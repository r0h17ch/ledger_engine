import pytest
from ledger_engine.engine import LedgerEngine

@pytest.fixture
def bank():
    engine = LedgerEngine()
    engine.create_account("alice")
    engine.create_account("bob")
    return engine

def test_create_account(bank):
    assert bank.get_balance("alice") == 0

def test_deposit(bank):
    bank.deposit("alice", 1000)
    assert bank.get_balance("alice") == 1000

def test_withdraw(bank):
    bank.deposit("alice", 1000)
    bank.withdraw("alice", 300)
    assert bank.get_balance("alice") == 700

def test_transfer(bank):
    bank.deposit("alice", 1000)
    bank.transfer("alice", "bob", 400)
    assert bank.get_balance("alice") == 600
    assert bank.get_balance("bob") == 400

def test_insufficient_funds(bank):
    with pytest.raises(ValueError):
        bank.withdraw("alice", 500)
    assert bank.get_balance("alice") == 0

def test_failed_transfer_does_not_modify_ledger(bank):
    bank.deposit("alice", 100)
    previouse_entries = len(bank.entries)
    with pytest.raises(ValueError):
        bank.transfer("alice", "bob", 500)
    assert len(bank.entries) == previouse_entries
    assert bank.get_balance("alice") == 100
    assert bank.get_balance("bob") == 0

def test_negative_deposit_rejected(bank):
    with pytest.raises(ValueError):
        bank.deposit("alice" , -100)

def test_duplicate_account_rejected(bank):
    with pytest.raises(ValueError):
        bank.create_account("alice")

def test_transaction_entries_are_balanced(bank):
    bank.deposit("alice", 1000)
    bank.transfer("alice", "bob", 400)
    total_debit = sum(e["debit"] for e in bank.entries)
    total_credit = sum(e["credit"] for e in bank.entries)
    assert total_credit == total_debit