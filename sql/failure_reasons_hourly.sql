-- Why transactions are failing today: provider response code and message per hour.
SELECT
    to_char(created_at, 'HH24')                  AS hour,
    provider,
    status,
    response_code || ' -> ' || response_message  AS provider_response,
    count(*)                                     AS txn_count
FROM transactions
WHERE created_at >= date_trunc('day', now())
  AND status <> 'SUCCESS'
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 5 DESC;
