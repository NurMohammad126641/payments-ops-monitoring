-- Anomaly rule: not-successful transactions per provider in the last 60 minutes, compared with
-- the average for the same hour of day over the previous 28 days.
-- Must return exactly three columns: key, current_count, baseline_avg.
WITH current_window AS (
    SELECT provider, count(*) AS current_count
    FROM transactions
    WHERE status <> 'SUCCESS'
      AND created_at >= now() - interval '60 minutes'
    GROUP BY provider
),
baseline AS (
    SELECT provider, count(*) / 28.0 AS baseline_avg
    FROM transactions
    WHERE status <> 'SUCCESS'
      AND created_at >= date_trunc('day', now()) - interval '28 days'
      AND created_at <  date_trunc('day', now())
      AND extract(hour FROM created_at) = extract(hour FROM now())
    GROUP BY provider
)
SELECT
    c.provider                          AS key,
    c.current_count,
    round(coalesce(b.baseline_avg, 0), 2) AS baseline_avg
FROM current_window c
LEFT JOIN baseline b USING (provider)
ORDER BY c.provider;
