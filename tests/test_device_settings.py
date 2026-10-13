"""Tests for PowerAnt device settings."""

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
    and node.name == "_get_device_settings"
)

module = ast.Module(body=[function], type_ignores=[])

namespace = {}

exec(compile(module, str(SOURCE), "exec"), namespace)

get_settings = namespace["_get_device_settings"]


class TestDeviceSettings(unittest.TestCase):

    def test_normal_settings(self):
        device = {
            "mode": "time_slots",
            "cheapest_hours": 12.5,
            "price_trigger": 4,
            "time_slots": 3,
        }

        self.assertEqual(
            get_settings(device),
            ("time_slots", 12.5, 4.0, 3),
        )

    def test_missing_settings(self):
        self.assertEqual(
            get_settings({}),
            ("", 0.0, 0.0, 1),
        )

    def test_zero_settings(self):
        device = {
            "mode": "off",
            "cheapest_hours": 0,
            "price_trigger": 0,
            "time_slots": 0,
        }

        self.assertEqual(
            get_settings(device),
            ("off", 0.0, 0.0, 1),
        )


if __name__ == "__main__":
    unittest.main()
