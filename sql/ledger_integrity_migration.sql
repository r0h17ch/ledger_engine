-- add posting timestamp
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS posted_at TIMESTAMPTZ;

-- existing transactions already have a ledger entries.
-- marking them as posted
UPDATE transactions
SET posted_at = created_at
WHERE posted_at IS NULL;

-- ensuring new transactions cannot silently remain drafts
ALTER TABLE transactions
ALTER COLUMN posted_at SET NOT NULL;