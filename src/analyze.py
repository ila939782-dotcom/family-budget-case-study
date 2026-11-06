"""Execute the measurement specification against illustrative event logs."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
FORMAT = '%Y-%m-%d %H:%M:%S'
EVENTS = {'family_created', 'limit_set', 'report_viewed', 'budget_opened'}


def valid_time(value):
    result = datetime.strptime(value, FORMAT)
    if result.strftime(FORMAT) != value:
        raise ValueError('Timestamps must be canonical UTC YYYY-MM-DD HH:MM:SS')
    return result


def read_csv(path):
    with Path(path).open(encoding='utf-8') as f:
        return list(csv.DictReader(f))


def connect(exposures, events):
    users = set()
    for row in exposures:
        valid_time(row['exposed_at'])
        if not row['user_id'] or row['user_id'] in users:
            raise ValueError('Exposure user IDs must be nonempty and unique')
        users.add(row['user_id'])
    seen = {}
    for row in events:
        valid_time(row['occurred_at'])
        if not row['event_id'] or row['user_id'] not in users or row['event_name'] not in EVENTS:
            raise ValueError('Invalid event identity, owner or event name')
        payload = (row['user_id'], row['event_name'], row['occurred_at'])
        if row['event_id'] in seen and seen[row['event_id']] != payload:
            raise ValueError(f'Conflicting payload for event ID {row["event_id"]}')
        seen[row['event_id']] = payload
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript((ROOT / 'sql/schema.sql').read_text())
    conn.executemany('INSERT INTO exposures VALUES (:user_id, :exposed_at)', exposures)
    conn.executemany('INSERT INTO raw_events VALUES (:event_id, :user_id, :event_name, :occurred_at)', events)
    return conn


def calculate(conn, as_of):
    valid_time(as_of)
    rows = [dict(row) for row in conn.execute((ROOT / 'sql/user_metrics.sql').read_text(), {'as_of': as_of})]
    mature = [r for r in rows if r['funnel_mature']]
    retained_cohort = [r for r in rows if r['d14_mature']]
    ratio = lambda n, d: n / d if d else None
    counts = [len(mature)] + [sum(r[k] is not None for r in mature) for k in ('created_at', 'limited_at', 'activated_at')]
    names = ['Exposed', 'Family created', 'Limit set', 'Report viewed (activated)']
    funnel = [dict(stage=name, users=count, conversion_from_exposure=ratio(count, counts[0]),
                   conversion_from_previous=ratio(count, counts[i-1]) if i else None)
              for i, (name, count) in enumerate(zip(names, counts))]
    retained = sum(r['retained_d14'] for r in retained_cohort)
    raw_count = conn.execute('SELECT COUNT(*) FROM raw_events WHERE occurred_at < ?', (as_of,)).fetchone()[0]
    unique_count = conn.execute('SELECT COUNT(DISTINCT event_id) FROM raw_events WHERE occurred_at < ?', (as_of,)).fetchone()[0]
    summary = dict(data_kind='synthetic demonstration; not production results', as_of_exclusive_utc=as_of,
                   exposed_users=len(rows), mature_funnel_users=counts[0],
                   excluded_immature_funnel_users=len(rows)-counts[0], activated_users=counts[-1],
                   activation_rate=ratio(counts[-1], counts[0]),
                   d14_eligible_activated_users=len(retained_cohort), retained_d14_users=retained,
                   retention_d14=ratio(retained, len(retained_cohort)),
                   repeated_event_deliveries=raw_count-unique_count)
    return rows, funnel, summary


def write_csv(path, rows):
    if not rows:
        return
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)


def run(data, output, as_of):
    output.mkdir(parents=True, exist_ok=True)
    with connect(read_csv(data/'exposures.csv'), read_csv(data/'events.csv')) as conn:
        rows, funnel, summary = calculate(conn, as_of)
    write_csv(output/'user_metrics.csv', rows)
    write_csv(output/'funnel.csv', funnel)
    (output/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=ROOT/'data')
    p.add_argument('--out', type=Path, default=ROOT/'reports')
    p.add_argument('--as-of', default='2026-02-01 00:00:00')
    a = p.parse_args(); run(a.data, a.out, a.as_of)
