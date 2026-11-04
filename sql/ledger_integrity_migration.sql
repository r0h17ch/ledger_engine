-- add posting timestamp
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS posted_at TIMESTAMPTZ;

-- existing transactions already have a ledger entries.
-- marking them as posted
UPDATE transactions
SET posted_at = created_at
WHERE posted_at IS NULL;


-- validate the complete transactiona at commit time
CREATE OR REPLACE FUNCTION validate_posted_transaction()
RETURNS TRIGGER AS $$
DECLARE
    entry_count BIGINT;
    total_debit NUMERIC;
    total_credit NUMERIC;
    current_posted_at TIMESTAMPTZ;
BEGIN
    -- Read the final transaction state.
    SELECT posted_at
    INTO current_posted_at
    FROM transactions
    WHERE id = NEW.id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- A transaction must be posted before commit.
    IF current_posted_at IS NULL THEN
        RAISE EXCEPTION
            'Transaction % cannot be committed without posting',
            NEW.id;
    END IF;

    SELECT
        COUNT(*),
        COALESCE(SUM(debit), 0),
        COALESCE(SUM(credit), 0)
    INTO
        entry_count,
        total_debit,
        total_credit
    FROM ledger_entries
    WHERE transaction_id = NEW.id;

    IF entry_count < 2 THEN
        RAISE EXCEPTION
            'Transaction % must contain at least two entries',
            NEW.id;
    END IF;

    IF total_debit <> total_credit THEN
        RAISE EXCEPTION
            'Unbalanced transaction %. Debits: %, Credits: %',
            NEW.id,
            total_debit,
            total_credit;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER check_transaction_balance
AFTER INSERT OR UPDATE ON transactions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION validate_posted_transaction();

-- prevent changes to posted ledger entries.
CREATE OR REPLACE FUNCTION protect_posted_ledger_entries()
RETURNS TRIGGER AS $$
DECLARE
    target_transaction_id UUID;
    transaction_posted_at TIMESTAMPTZ;
BEGIN
    IF TG_OP = 'UPDATE' THEN 
        target_transaction_id := OLD.transaction_id;
    ELSE
        target_transaction_id := NEW.transaction_id;
    END IF;

    SELECT posted_at
    INTO transaction_posted_at
    FROM transactions
    WHERE id = target_transaction_id
    FOR UPDATE;

    IF transaction_posted_at IS NOT NULL THEN
        RAISE EXCEPTION
            'Cannot modify entries of a posted transaction';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER protect_ledger_entries 
BEFORE INSERT OR UPDATE OR DELETE ON ledger_entries
FOR EACH ROW 
EXECUTE FUNCTION protect_posted_ledger_entries();