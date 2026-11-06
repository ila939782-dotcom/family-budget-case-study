import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from analyze import connect, calculate


def event(n, name, timestamp, user='u1'):
    return dict(event_id=str(n), user_id=user, event_name=name, occurred_at=timestamp)


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.exposure = [dict(user_id='u1', exposed_at='2026-01-01 00:00:00')]
        self.complete = [event(1, 'family_created', '2026-01-01 01:00:00'),
                         event(2, 'limit_set', '2026-01-01 02:00:00'),
                         event(3, 'report_viewed', '2026-01-01 03:00:00')]

    def calc(self, events, cutoff='2026-02-01 00:00:00', exposures=None):
        with connect(self.exposure if exposures is None else exposures, events) as conn:
            return calculate(conn, cutoff)

    def test_duplicates_and_delivery_order(self):
        _, _, s = self.calc(list(reversed(self.complete)) + [self.complete[0]])
        self.assertEqual(s['activation_rate'], 1)
        self.assertEqual(s['repeated_event_deliveries'], 1)

    def test_steps_must_be_ordered(self):
        events = [event(1,'limit_set','2026-01-01 01:00:00'),
                  event(2,'family_created','2026-01-01 02:00:00'),
                  event(3,'report_viewed','2026-01-01 03:00:00')]
        _, funnel, s = self.calc(events)
        self.assertEqual([r['users'] for r in funnel], [1,1,0,0])
        self.assertEqual(s['activation_rate'], 0)

    def test_exclusive_activation_boundary(self):
        events = self.complete[:2] + [event(3,'report_viewed','2026-01-08 00:00:00')]
        self.assertEqual(self.calc(events)[2]['activated_users'], 0)

    def test_immature_and_empty_denominators_are_not_zero(self):
        self.assertIsNone(self.calc(self.complete, '2026-01-07 00:00:00')[2]['activation_rate'])
        self.assertIsNone(self.calc([], exposures=[])[2]['retention_d14'])

    def test_retention_exact_day_and_full_observation(self):
        events = self.complete + [event(4,'budget_opened','2026-01-15 23:59:59')]
        self.assertIsNone(self.calc(events,'2026-01-15 23:59:59')[2]['retention_d14'])
        self.assertEqual(self.calc(events,'2026-01-16 00:00:00')[2]['retention_d14'], 1)
        events[-1] = event(4,'budget_opened','2026-01-16 00:00:00')
        self.assertEqual(self.calc(events)[2]['retention_d14'], 0)

    def test_pre_exposure_events_do_not_activate(self):
        events = [event(1,'family_created','2025-12-31 23:00:00')] + self.complete[1:]
        self.assertEqual(self.calc(events)[2]['activated_users'], 0)

    def test_conflicts_unknown_users_and_invalid_time_fail(self):
        for bad in (event(1,'limit_set','2026-01-01 01:00:00'),
                    event(5,'limit_set','2026-01-01 01:00:00','missing'),
                    event(5,'limit_set','2026-13-01 01:00:00')):
            with self.assertRaises(ValueError):
                connect(self.exposure, self.complete+[bad])


if __name__ == '__main__':
    unittest.main()
