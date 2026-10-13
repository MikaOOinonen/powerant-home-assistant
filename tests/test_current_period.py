"""Tests for current electricity price period lookup."""

import ast
from datetime import datetime
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
    and node.name == "_find_current_period"
)

module = ast.Module(body=[function], type_ignores=[])
namespace = {"datetime": datetime}

exec(compile(module, str(SOURCE), "exec"), namespace)

find_current_period = namespace["_find_current_period"]


class TestCurrentPeriod(unittest.TestCase):

    def test_15_minute_period(self):
        entries = [
            {"timestamp": "202610130800"},
            {"timestamp": "202610130815"},
            {"timestamp": "202610130830"},
            {"timestamp": "202610130845"},
        ]

        now = datetime(2026, 10, 13, 8, 23)

        result = find_current_period(entries, now, True)

        self.assertEqual(result, (1, "202610130815"))

    def test_60_minute_period(self):
        entries = [
            {"timestamp": "2026101308"},
            {"timestamp": "2026101309"},
        ]

        now = datetime(2026, 10, 13, 8, 45)

        result = find_current_period(entries, now, False)

        self.assertEqual(result, (0, "2026101308"))

    def test_period_not_found(self):
        entries = [
            {"timestamp": "202610130800"},
        ]

        now = datetime(2026, 10, 13, 9, 15)

        result = find_current_period(entries, now, True)

        self.assertEqual(result, (None, "202610130915"))


if __name__ == "__main__":
    unittest.main()
