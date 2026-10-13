"""Tests for PowerAnt TIME_SLOTS scheduling."""

import ast
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
    / "coordinator.py"
)

tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

function = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_apply_time_slots"
)

module = ast.Module(body=[function], type_ignores=[])

namespace = {}

exec(compile(module, str(SOURCE), "exec"), namespace)

apply_time_slots = namespace["_apply_time_slots"]


class TestTimeSlots(unittest.TestCase):

    def test_15_minute_equal_distribution(self):
        # 8 periods = 2 hours
        # 2 slots, 1 hour of operation
        # Each slot selects its 2 cheapest periods.

        prices = [
            1, 2, 3, 4,
            10, 20, 30, 40,
        ]

        entries = [
            {
                "timestamp": f"2026101300{i:02d}",
                "effective": float(price),
                "rule": "",
            }
            for i, price in enumerate(prices)
        ]

        apply_time_slots(
            entries,
            cheapest_hours=1,
            time_slots=2,
            period_minutes=15,
        )

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [
                True, True, False, False,
                True, True, False, False,
            ],
        )

    def test_60_minute_round_based_selection(self):
        # 24 hours, divided into 2 slots of 12 hours.
        #
        # Slot 1 cheapest prices: 1, 2, 3
        # Slot 2 cheapest prices: 4, 20, 30
        #
        # With 3 operating hours:
        # Round 1 selects 1 and 4.
        # Round 2 selects 2 (instead of 20).

        prices = [
            1, 2, 3, 50, 50, 50,
            50, 50, 50, 50, 50, 50,
            4, 20, 30, 50, 50, 50,
            50, 50, 50, 50, 50, 50,
        ]

        entries = [
            {
                "timestamp": f"20261013{hour:02d}00",
                "effective": float(price),
                "rule": "",
            }
            for hour, price in enumerate(prices)
        ]

        apply_time_slots(
            entries,
            cheapest_hours=3,
            time_slots=2,
            period_minutes=60,
        )

        selected_hours = [
            hour
            for hour, entry in enumerate(entries)
            if entry["is_on"]
        ]

        self.assertEqual(selected_hours, [0, 1, 12])

    def test_15_minute_uneven_distribution(self):
        # 5 quarter-hour periods across 2 slots.
        # Slot 1 gets 3 periods, slot 2 gets 2.

        prices = [
            1, 2, 3, 4,
            10, 20, 30, 40,
        ]

        entries = [
            {
                "timestamp": f"2026101300{i:02d}",
                "effective": float(price),
                "rule": "",
            }
            for i, price in enumerate(prices)
        ]

        apply_time_slots(
            entries,
            cheapest_hours=1.25,
            time_slots=2,
            period_minutes=15,
        )

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [
                True, True, True, False,
                True, True, False, False,
            ],
        )


if __name__ == "__main__":
    unittest.main()
