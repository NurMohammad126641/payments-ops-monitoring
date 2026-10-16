-- Today's transaction volume per hour, provider, direction and status.
SELECT
    to_char(created_at, 'HH24') AS hour,
    provider,
    direction,
    status,
    count(*)                    AS txn_count,
    sum(amount)                 AS txn_amount
FROM transactions
WHERE created_at >= date_trunc('day', now())
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2, 3, 4;
