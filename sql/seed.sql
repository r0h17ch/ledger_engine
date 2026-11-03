INSERT INTO accounts (
    id,
    name,
    currency,
    balance,
    allow_negative_balance
)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'SYSTEM_CASH',
    'INR',
    0,
    TRUE
)
ON CONFLICT (id) DO NOTHING;