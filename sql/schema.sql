-- LEDGER ENGINE : INITIAL DATABASE SCHEMA

-- 1. ACCOUNTS
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name VARCHAR(100) NOT NULL,

    currency CHAR(3) NOT NULL,

    -- Balance is stored in minor currency units. eg : $100.50 = 10050 cents
    balance BIGINT NOT NULL DEFAULT 0,

    -- Special accounts can be allowed to go negative
    allow_negative_balance BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(id,currency),

    CHECK (
        allow_negative_balance = TRUE
        OR balance >= 0
    )
);

-- 2. TRANSACTIONS
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    reference VARCHAR(100) UNIQUE,

    description TEXT,

    currency CHAR(3) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (id, currency)
);

-- 3. LEDGER ENTRIES 
CREATE TABLE IF NOT EXISTS ledger_entries (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    transaction_id UUID NOT NULL,

    account_id UUID NOT NULL,

    currency CHAR(3) NOT NULL,

    debit BIGINT NOT NULL DEFAULT 0,

    credit BIGINT NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Both values cannot be negative
    CHECK (debit >= 0 AND credit >= 0),

    -- Exactly one side must contain a positive amount.
    CHECK (
        (debit > 0 AND credit = 0)
        OR 
        (credit > 0 AND debit = 0)
    ),

    -- Prevent entries from mixing currencies
    FOREIGN KEY (transaction_id, currency)
        REFERENCES transactions(id, currency),

    FOREIGN KEY (account_id, currency)
        REFERENCES accounts(id, currency)
);


-- 4. INDEXES
CREATE INDEX IF NOT EXISTS idx_ledger_account
    ON ledger_entries(account_id);

CREATE INDEX IF NOT EXISTS idx_ledger_transaction
    ON ledger_entries(transaction_id);

CREATE INDEX IF NOT EXISTS idx_ledger_created_ar
    ON ledger_entries(created_at)