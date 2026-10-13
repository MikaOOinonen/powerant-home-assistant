"""Tests for the next ON/OFF change calculation."""

import ast
from datetime import datetime
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
    / "schedule.py"
)

# Load only the function under test.
# This avoids importing Home Assistant dependencies.
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

function = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_find_next_change"
)

module = ast.Module(body=[function], type_ignores=[])
namespace = {"datetime": datetime}
exec(compile(module, str(SOURCE), "exec"), namespace)

find_next_change = namespace["_find_next_change"]


class TestNextChange(unittest.TestCase):

    def test_change_today(self):
        entries = [
            {"timestamp": "202610130800", "is_on": False},
            {"timestamp": "202610130815", "is_on": False},
            {"timestamp": "202610130830", "is_on": True},
        ]

        result = find_next_change(
            entries, [], 0, "%Y%m%d%H%M"
        )

        self.assertEqual(
            result,
            {"time": "08:30", "state": True},
        )

    def test_change_tomorrow(self):
        entries = [
            {"timestamp": "202610132345", "is_on": True},
        ]

        tomorrow = [
            {"timestamp": "202610140000", "is_on": True},
            {"timestamp": "202610140015", "is_on": False},
        ]

        result = find_next_change(
            entries, tomorrow, 0, "%Y%m%d%H%M"
        )

        self.assertEqual(
            result,
            {"time": "00:15", "state": False},
        )

    def test_no_change(self):
        entries = [
            {"timestamp": "202610130800", "is_on": False},
            {"timestamp": "202610130815", "is_on": False},
        ]

        result = find_next_change(
            entries, [], 0, "%Y%m%d%H%M"
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
