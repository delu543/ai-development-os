import unittest
from agenda import entries


class ScheduleTests(unittest.TestCase):
    def test_day_shift(self):
        rows = [dict(id="a", start="2026-11-25T09:00:00+00:00", cancelled=False)]
        self.assertEqual(entries("2026-11-25", rows), ["a"])
