"""Tests for PowerAnt savings calculation."""

import ast
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
    / "savings.py"
)

tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

function = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "calculate_savings"
)

module = ast.Module(body=[function], type_ignores=[])

namespace = {
    "Sequence": __import__("collections.abc", fromlist=["Sequence"]).Sequence,
    "Mapping": __import__("collections.abc", fromlist=["Mapping"]).Mapping,
    "Any": __import__("typing").Any,
}

exec(compile(module, str(SOURCE), "exec"), namespace)

calculate_savings = namespace["calculate_savings"]


class TestSavings(unittest.TestCase):
    """Test savings calculation."""

    def test_savings_15_and_60_minutes(self):
        """Verify both price resolutions."""

        for periods_per_hour in (4, 1):
            with self.subTest(periods_per_hour=periods_per_hour):
                schedule = []

                for hour in range(24):
                    for _ in range(periods_per_hour):
                        schedule.append({
                            "price": 1.0 if hour < 5 else 5.0,
                            "is_on": hour < 5,
                        })

                self.assertEqual(
                    len(schedule),
                    24 * periods_per_hour,
                )

                expected = (1 - 1 / (100 / 24)) * 100

                self.assertAlmostEqual(
                    calculate_savings(schedule),
                    expected,
                )

    def test_empty_schedule(self):
        self.assertIsNone(calculate_savings([]))

    def test_all_on(self):
        schedule = [
            {"price": 2.0, "is_on": True},
            {"price": 4.0, "is_on": True},
        ]

        self.assertAlmostEqual(calculate_savings(schedule), 0.0)

    def test_all_off(self):
        schedule = [
            {"price": 2.0, "is_on": False},
            {"price": 4.0, "is_on": False},
        ]

        self.assertAlmostEqual(calculate_savings(schedule), 100.0)

    def test_negative_savings(self):
        schedule = [
            {"price": 1.0, "is_on": False},
            {"price": 5.0, "is_on": True},
        ]

        self.assertAlmostEqual(
            calculate_savings(schedule),
            ((3.0 - 5.0) / 3.0) * 100,
        )

    def test_zero_average(self):
        schedule = [
            {"price": 0.0, "is_on": True},
            {"price": 0.0, "is_on": False},
        ]

        self.assertAlmostEqual(calculate_savings(schedule), 0.0)

    def test_forced_on_off(self):
        schedule = [
            {"price": 1.0, "is_on": False, "rule": "OFF"},
            {"price": 5.0, "is_on": True, "rule": "ON"},
        ]

        self.assertAlmostEqual(
            calculate_savings(schedule),
            ((3.0 - 5.0) / 3.0) * 100,
        )


if __name__ == "__main__":
    unittest.main()
