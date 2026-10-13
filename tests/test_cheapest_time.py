"""Tests for PowerAnt cheapest time scheduling."""

import ast
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
    / "schedule.py"
)

tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

function = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_apply_cheapest_time"
)

module = ast.Module(body=[function], type_ignores=[])

namespace = {}

exec(compile(module, str(SOURCE), "exec"), namespace)

apply_cheapest_time = namespace["_apply_cheapest_time"]


class TestCheapestTime(unittest.TestCase):

    def test_15_minute_resolution(self):
        entries = [
            {
                "timestamp": f"2026101300{i:02d}",
                "effective": price,
                "rule": "",
            }
            for i, price in enumerate(
                [8, 2, 5, 1, 7, 3, 6, 4]
            )
        ]

        apply_cheapest_time(entries, 1, 15)

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [False, True, False, True,
             False, True, False, True],
        )

    def test_60_minute_resolution(self):
        entries = [
            {
                "timestamp": f"20261013{i:02d}",
                "effective": price,
                "rule": "",
            }
            for i, price in enumerate(
                [5, 2, 8, 1, 4, 3]
            )
        ]

        apply_cheapest_time(entries, 2, 60)

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [False, True, False, True, False, False],
        )

    def test_fractional_hours_15_minute(self):
        entries = [
            {
                "timestamp": f"20261013{i:04d}",
                "effective": float(40 - i),
                "rule": "",
            }
            for i in range(40)
        ]

        apply_cheapest_time(entries, 6.25, 15)

        selected = [
            entry for entry in entries
            if entry["is_on"]
        ]

        self.assertEqual(len(selected), 25)

        self.assertEqual(
            sorted(entry["effective"] for entry in selected),
            [float(i) for i in range(1, 26)],
        )

    def test_forced_on_excluded_from_cheapest_selection(self):
        entries = [
            {
                "timestamp": "202610130000",
                "effective": 1.0,
                "rule": "ON",
            },
            {
                "timestamp": "202610130015",
                "effective": 2.0,
                "rule": "",
            },
            {
                "timestamp": "202610130030",
                "effective": 3.0,
                "rule": "",
            },
            {
                "timestamp": "202610130045",
                "effective": 4.0,
                "rule": "",
            },
        ]

        apply_cheapest_time(entries, 0.5, 15)

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [False, True, True, False],
        )

    def test_forced_off_included_in_cheapest_selection(self):
        entries = [
            {
                "timestamp": "202610130000",
                "effective": 1.0,
                "rule": "OFF",
            },
            {
                "timestamp": "202610130015",
                "effective": 2.0,
                "rule": "",
            },
            {
                "timestamp": "202610130030",
                "effective": 3.0,
                "rule": "",
            },
            {
                "timestamp": "202610130045",
                "effective": 4.0,
                "rule": "",
            },
        ]

        apply_cheapest_time(entries, 0.5, 15)

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [True, True, False, False],
        )


if __name__ == "__main__":
    unittest.main()
