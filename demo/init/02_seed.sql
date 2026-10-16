-- Synthetic demo data: 30 days of random transactions across five providers, plus a spike of
-- ROCKET gateway timeouts in the last hour so the anomaly rule has something to find.
-- No real customer, merchant or transaction data is used anywhere in this project.

WITH base AS (
    SELECT
        now() - random() * interval '30 days'                              AS created_at,
        (ARRAY['BKASH', 'NAGAD', 'ROCKET', 'NPSB', 'VISA'])[1 + floor(random() * 5)::int]
                                                                            AS provider,
        CASE WHEN random() < 0.55 THEN 'MONEY_IN' ELSE 'MONEY_OUT' END      AS direction,
        random()                                                            AS r_status,
        random()                                                            AS r_reason,
        round((50 + random() * 9950)::numeric, 2)                          AS amount
    FROM generate_series(1, 120000)
)
INSERT INTO transactions
    (created_at, provider, direction, status, amount, response_code, response_message)
SELECT
    created_at,
    provider,
    direction,
    CASE
        WHEN r_status < 0.93 THEN 'SUCCESS'
        WHEN r_status < 0.98 THEN 'FAILED'
        ELSE 'PENDING'
    END,
    amount,
    CASE
        WHEN r_status < 0.93 THEN '000'
        WHEN r_status >= 0.98 THEN 'P100'
        WHEN r_reason < 0.40 THEN 'E504'
        WHEN r_reason < 0.70 THEN 'E402'
        WHEN r_reason < 0.90 THEN 'E401'
        ELSE 'E500'
    END,
    CASE
        WHEN r_status < 0.93 THEN 'Success'
        WHEN r_status >= 0.98 THEN 'Awaiting provider callback'
        WHEN r_reason < 0.40 THEN 'Gateway timeout'
        WHEN r_reason < 0.70 THEN 'Insufficient balance'
        WHEN r_reason < 0.90 THEN 'Invalid PIN'
        ELSE 'Provider internal error'
    END
FROM base;

-- Incident: ROCKET money-out gateway timing out during the last hour.
INSERT INTO transactions
    (created_at, provider, direction, status, amount, response_code, response_message)
SELECT
    now() - random() * interval '50 minutes',
    'ROCKET',
    'MONEY_OUT',
    'FAILED',
    round((100 + random() * 4900)::numeric, 2),
    'E504',
    'Gateway timeout'
FROM generate_series(1, 150);

ANALYZE transactions;
