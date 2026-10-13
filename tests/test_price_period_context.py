"""Tests for PowerAnt price period context."""

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
    / "prices.py"
)

tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

function = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_get_price_period_context"
)

module = ast.Module(body=[function], type_ignores=[])

namespace = {
    "datetime": datetime,
    "timedelta": timedelta,
}

exec(compile(module, str(SOURCE), "exec"), namespace)

get_context = namespace["_get_price_period_context"]


class TestPricePeriodContext(unittest.TestCase):

    def test_15_minute_resolution(self):
        now = datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc)

        result = get_context(
            {"offset_hour": 3},
            "finland-fi1_15m",
            now,
        )

        self.assertEqual(result[0].hour, 11)
        self.assertEqual(result[1], "20261013")
        self.assertEqual(result[2], "20261014")
        self.assertTrue(result[3])
        self.assertEqual(result[4], 15)
        self.assertEqual(result[5], "%Y%m%d%H%M")

    def test_60_minute_resolution(self):
        now = datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc)

        result = get_context(
            {"offset_hour": 2},
            "finland-fi1",
            now,
        )

        self.assertEqual(result[0].hour, 10)
        self.assertFalse(result[3])
        self.assertEqual(result[4], 60)
        self.assertEqual(result[5], "%Y%m%d%H")

    def test_midnight_rollover(self):
        now = datetime(2026, 10, 13, 22, 30, tzinfo=timezone.utc)

        result = get_context(
            {"offset_hour": 3},
            "finland-fi1_15m",
            now,
        )

        self.assertEqual(result[1], "20261014")
        self.assertEqual(result[2], "20261015")
        self.assertEqual(result[0].hour, 1)
        self.assertEqual(result[0].minute, 30)


if __name__ == "__main__":
    unittest.main()
