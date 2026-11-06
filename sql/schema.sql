PRAGMA foreign_keys = ON;
CREATE TABLE exposures (
    user_id TEXT PRIMARY KEY,
    exposed_at TEXT NOT NULL
);
-- Raw deliveries may repeat an event_id. event_id identifies one logical event.
CREATE TABLE raw_events (
    event_id TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES exposures(user_id),
    event_name TEXT NOT NULL CHECK (event_name IN
        ('family_created', 'limit_set', 'report_viewed', 'budget_opened')),
    occurred_at TEXT NOT NULL
);
CREATE INDEX idx_events_user_time ON raw_events(user_id, occurred_at);
