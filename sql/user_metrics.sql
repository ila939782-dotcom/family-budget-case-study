-- SQLite 3.25+. :as_of is an EXCLUSIVE UTC cutoff (YYYY-MM-DD HH:MM:SS).
-- Input validation rejects conflicting event IDs. DISTINCT removes retries.
WITH deduplicated AS (
    SELECT DISTINCT event_id, user_id, event_name, occurred_at
    FROM raw_events
    WHERE occurred_at < :as_of
),
cohort AS (
    SELECT user_id, exposed_at,
           datetime(exposed_at, '+7 days') AS window_end,
           CASE WHEN datetime(exposed_at, '+7 days') <= :as_of THEN 1 ELSE 0 END AS funnel_mature
    FROM exposures
    WHERE exposed_at < :as_of
),
created AS (
    SELECT c.*, MIN(e.occurred_at) AS created_at
    FROM cohort c
    LEFT JOIN deduplicated e ON e.user_id = c.user_id
        AND e.event_name = 'family_created'
        AND e.occurred_at >= c.exposed_at AND e.occurred_at < c.window_end
    GROUP BY c.user_id
),
limited AS (
    SELECT c.*, MIN(e.occurred_at) AS limited_at
    FROM created c
    LEFT JOIN deduplicated e ON e.user_id = c.user_id
        AND e.event_name = 'limit_set'
        AND e.occurred_at >= c.created_at AND e.occurred_at < c.window_end
    GROUP BY c.user_id
),
activated AS (
    SELECT l.*, MIN(e.occurred_at) AS activated_at
    FROM limited l
    LEFT JOIN deduplicated e ON e.user_id = l.user_id
        AND e.event_name = 'report_viewed'
        AND e.occurred_at >= l.limited_at AND e.occurred_at < l.window_end
    GROUP BY l.user_id
)
SELECT a.*,
    CASE WHEN a.activated_at IS NOT NULL
        AND datetime(date(a.activated_at, '+15 days')) <= :as_of
        THEN 1 ELSE 0 END AS d14_mature,
    CASE WHEN a.activated_at IS NOT NULL
        AND datetime(date(a.activated_at, '+15 days')) <= :as_of
        AND EXISTS (
            SELECT 1 FROM deduplicated e
            WHERE e.user_id = a.user_id
              AND e.event_name = 'budget_opened'
              AND e.occurred_at >= datetime(date(a.activated_at, '+14 days'))
              AND e.occurred_at < datetime(date(a.activated_at, '+15 days'))
        ) THEN 1 ELSE 0 END AS retained_d14
FROM activated a
ORDER BY user_id;
