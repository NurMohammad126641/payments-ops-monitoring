-- Health of each provider over the last 24 hours.
SELECT
    provider,
    count(*)                                           AS total,
    count(*) FILTER (WHERE status = 'SUCCESS')         AS success,
    count(*) FILTER (WHERE status = 'FAILED')          AS failed,
    count(*) FILTER (WHERE status = 'PENDING')         AS pending,
    round(100.0 * count(*) FILTER (WHERE status = 'SUCCESS') / nullif(count(*), 0), 2)
                                                       AS success_rate_pct
FROM transactions
WHERE created_at >= now() - interval '24 hours'
GROUP BY provider
ORDER BY success_rate_pct;
