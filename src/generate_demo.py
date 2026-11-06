"""Create deterministic artificial events. No personal or bank data is used."""
import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]


def generate(output):
    rng = random.Random(21)
    exposures, events = [], []
    start = datetime(2026, 1, 1, 10)
    def emit(user, name, stamp):
        row = dict(event_id=f'evt_{len(events):05d}', user_id=user,
                   event_name=name, occurred_at=stamp.strftime('%Y-%m-%d %H:%M:%S'))
        events.append(row)
        if rng.random() < 0.08:
            events.append(dict(row))
    for i in range(300):
        user = f'demo_{i:04d}'
        exposed = start + timedelta(days=i % 30)
        exposures.append(dict(user_id=user, exposed_at=exposed.strftime('%Y-%m-%d %H:%M:%S')))
        if rng.random() < 0.12:  # An orphan step must not create a successful funnel.
            emit(user, 'limit_set', exposed + timedelta(minutes=1))
        if rng.random() < 0.73:
            created = exposed + timedelta(hours=rng.randint(1, 30))
            emit(user, 'family_created', created)
            if rng.random() < 0.64:
                limited = created + timedelta(hours=rng.randint(1, 30))
                emit(user, 'limit_set', limited)
                if rng.random() < 0.78:
                    activated = limited + timedelta(hours=rng.randint(1, 30))
                    emit(user, 'report_viewed', activated)
                    if rng.random() < 0.42:
                        emit(user, 'budget_opened', activated + timedelta(days=14))
        if i % 11 == 0:  # Too late to count in the activation window.
            emit(user, 'report_viewed', exposed + timedelta(days=8))
    rng.shuffle(events)
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in [('exposures', exposures), ('events', events)]:
        with (output/f'{name}.csv').open('w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=rows[0]); w.writeheader(); w.writerows(rows)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT/'data')
    generate(p.parse_args().out)
