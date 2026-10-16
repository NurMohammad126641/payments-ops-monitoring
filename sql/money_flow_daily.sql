-- Daily volume for the last 30 days. The most recent 5 minutes are excluded because
-- provider callbacks for those transactions may still be arriving.
SELECT
    to_char(created_at, 'YYYY-MM-DD') AS day,
    provider,
    direction,
    status,
    count(*)                          AS txn_count,
    sum(amount)                       AS txn_amount
FROM transactions
WHERE created_at >= date_trunc('day', now()) - interval '30 days'
  AND created_at <= now() - interval '5 minutes'
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2, 3, 4;
