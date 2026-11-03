from uuid import uuid4
from threading import RLock
from ledger_engine.validation import validate_transaction

class LedgerEngine:

    SYSTEM_ACCOUNT = "SYSTEM_CASH"
    
    def __init__(self):
        self._lock = RLock()
        self.accounts = {self.SYSTEM_ACCOUNT}
        self.entries = []

    def create_account(self, account_id):
        with self._lock:
            if not account_id:
                raise ValueError("Account ID cannot be empty")

            if account_id in self.accounts:
                raise ValueError("Account already exists")

            self.accounts.add(account_id)

    def get_balance(self, account_id):
        with self._lock:
            if account_id not in self.accounts:
                raise ValueError("Account does not exist")
            
            balance = 0
            for entry in self.entries:
                if entry["account"] == account_id:
                    balance += (entry["credit"] - entry["debit"])

            return balance

    def _validate_amount(self, amount):
        if not isinstance(amount,int) or isinstance(amount,bool):
            raise ValueError("Amount must be an integer")
        if amount <= 0:
            raise ValueError("Amount must be positive")

    def _post_transaction(self, entries):
        with self._lock:
            if not validate_transaction(entries):
                raise ValueError("Invalid ledger transaction")
            
            for entry in entries:
                if entry["account"] not in self.accounts:
                    raise ValueError("Account does not exist")
                
            changes = {} #calculating the proposed balances without modifying the ledger
            for entry in entries:
                account = entry["account"]
                changes[account] = (
                    changes.get(account, self.get_balance(account))
                    + entry["credit"]
                    - entry["debit"]
                )

            # Wallet accounts must never become negative
            for account, new_balance in changes.items():
                if account != self.SYSTEM_ACCOUNT and new_balance < 0:
                    raise ValueError("Insufficient funds")
                
            transaction_id = str(uuid4())
            for entry in entries:
                self.entries.append({
                    **entry,
                    "transaction_id" : transaction_id
                })

            return transaction_id

    def deposit(self, account_id, amount):
        self._validate_amount(amount)
        entries = [
            {
                "account": self.SYSTEM_ACCOUNT,
                "debit": amount,
                "credit": 0
            },
            {
                "account" : account_id,
                "debit": 0,
                "credit": amount
            }
        ]
        return self._post_transaction(entries)

    def withdraw(self, account_id, amount):
        self._validate_amount(amount)
        entries = [
            {
                "account" : account_id,
                "debit" : amount,
                "credit" : 0
            },
            {
                "account" : self.SYSTEM_ACCOUNT,
                "debit" : 0,
                "credit" : amount
            }
        ]
        return self._post_transaction(entries)

    def transfer(self, source, destination, amount):
        self._validate_amount(amount)
        if source == destination:
            raise ValueError("Cannot transfer to same account")
        entries = [
            {
                "account" : source,
                "debit" : amount,
                "credit" : 0
            },
            {
                "account" : destination,
                "debit" : 0,
                "credit" : amount
            }
        ]
        return self._post_transaction(entries)