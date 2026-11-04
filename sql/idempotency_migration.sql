ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(255);

ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS request_hash CHAR(64);

-- PG permits multiple NULL values in a unique index
CREATE UNIQUE INDEX IF NOT EXISTS
    idx_transaction_idempotency_key
ON transactions(idempotency_key);