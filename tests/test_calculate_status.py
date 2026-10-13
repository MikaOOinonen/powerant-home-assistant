"""Tests for PowerAnt scheduling status calculation."""

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
    and node.name == "_calculate_status"
)

module = ast.Module(body=[function], type_ignores=[])

namespace = {
    "_apply_cheapest_time": lambda *args: None,
    "_apply_time_slots": lambda *args: None,
}

exec(compile(module, str(SOURCE), "exec"), namespace)

calculate_status = namespace["_calculate_status"]


class TestCalculateStatus(unittest.TestCase):

    def test_on_mode(self):
        entries = [
            {"effective": 2.0, "rule": ""},
            {"effective": 8.0, "rule": ""},
        ]

        calculate_status(entries, "on", 0, 0, 1, 15)

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [True, True],
        )

    def test_off_mode(self):
        entries = [
            {"effective": 2.0, "rule": ""},
            {"effective": 8.0, "rule": ""},
        ]

        calculate_status(entries, "off", 0, 0, 1, 15)

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [False, False],
        )


    def test_trigger_mode(self):
        entries = [
            {"effective": 2.0, "rule": ""},
            {"effective": 4.0, "rule": ""},
            {"effective": 8.0, "rule": ""},
        ]

        calculate_status(entries, "trigger", 0, 4, 1, 15)

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [True, False, False],
        )

    def test_tariff_forces_on(self):
        entries = [
            {"effective": 8.0, "rule": "ON"},
            {"effective": 8.0, "rule": ""},
        ]

        calculate_status(entries, "off", 0, 0, 1, 15)

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [True, False],
        )

    def test_tariff_forces_off(self):
        entries = [
            {"effective": 2.0, "rule": "OFF"},
            {"effective": 2.0, "rule": ""},
        ]

        calculate_status(entries, "on", 0, 0, 1, 15)

        self.assertEqual(
            [entry["is_on"] for entry in entries],
            [False, True],
        )

    def test_reverse_or_tariff_on(self):
        entries = [
            {
                "effective": 8.0,
                "rule": "ON",
                "is_on": False,
            },
        ]

        calculate_status(
            entries, "reverse_or", 0, 4, 1, 15
        )

        self.assertFalse(entries[0]["is_on"])

    def test_reverse_or_tariff_off(self):
        entries = [
            {
                "effective": 2.0,
                "rule": "OFF",
                "is_on": False,
            },
        ]

        calculate_status(
            entries, "reverse_or", 0, 4, 1, 15
        )

        self.assertTrue(entries[0]["is_on"])


if __name__ == "__main__":
    unittest.main()
