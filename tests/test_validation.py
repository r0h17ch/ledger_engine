from ledger_engine.validation import validate_transaction

def test_valid_transfer():
    entries = [
            {"account": "alice", "debit": 500, "credit": 0},
            {"account": "bob", "debit": 0, "credit": 500}
        ]

    assert validate_transaction(entries) is True


def test_unbalanced_transfer():
    entries = [
            {"account": "alice", "debit": 500, "credit": 0},
            {"account": "bob", "debit": 0, "credit": 400}
        ]

    assert validate_transaction(entries) is False

def test_boolean_amount_rejected():
    entries = [
        {"account": "alice", "debit": True, "credit": 0},
        {"account": "bob", "debit": 0, "credit": True}
    ]
    assert validate_transaction(entries) is False

def test_negative_amount_rejected():
    entries = [
        {"account": "alice", "debit": -500, "credit": 0},
        {"account": "bob", "debit": 0, "credit": -500}
    ]
    assert validate_transaction(entries) is False

def test_single_entry_rejected():
    entries = [
        {"account": "alice", "debit": 500, "credit": 0}
    ]
    assert validate_transaction(entries) is False

def test_empty_transaction_rejected():
    assert validate_transaction([]) is False