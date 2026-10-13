"""Tests for PowerAnt coordinator data construction."""

import ast
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
    / "device.py"
)


def load_function(name):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == name
    )

    module = ast.Module(
        body=[function],
        type_ignores=[],
    )

    helpers_source = SOURCE.with_name("helpers.py")
    helpers_tree = ast.parse(
        helpers_source.read_text(encoding="utf-8")
    )

    helper_names = {
        "_as_bool_or_none",
        "_as_float_or_none",
        "_as_int_or_none",
    }

    helper_functions = [
        node
        for node in helpers_tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in helper_names
    ]

    helpers_module = ast.Module(
        body=helper_functions,
        type_ignores=[],
    )

    namespace = {}

    exec(
        compile(helpers_module, str(helpers_source), "exec"),
        namespace,
    )

    exec(
        compile(module, str(SOURCE), "exec"),
        namespace,
    )

    return namespace[name]


class TestCoordinatorData(unittest.TestCase):

    def test_build_coordinator_data(self):
        build_data = load_function(
            "_build_coordinator_data"
        )

        device = {
            "device_name": "Water Heater",
            "cheapest_hours": "8.5",
            "price_trigger": "4.2",
            "time_slots": "3",
            "uses_tariffs": True,
            "child_lock": False,
            "tariff_8": "on",
        }

        metadata = {
            "product_key": "test-device",
            "device_model": "Powerant Switch 63A",
            "firmware_version": "3.14",
            "capabilities": ["switch"],
            "country_area": "finland-fi1_15m",
        }

        settings = {
            "mode": "time_slots",
            "cheapest_hours": 8.5,
            "time_slots": 3,
        }

        calculated = {
            "schedule": [{"timestamp": "202610130800"}],
            "tomorrow_schedule": [],
            "current": {
                "is_on": True,
                "price": 2.5,
            },
            "current_period": "08:00–08:15",
            "next_change": None,
        }

        result = build_data(
            device,
            metadata,
            settings,
            calculated,
        )

        expected = {
            "device": device,
            "device_name": "Water Heater",
            "device_model": "Powerant Switch 63A",
            "firmware_version": "3.14",
            "capabilities": ["switch"],
            "product_key": "test-device",
            "mode": "time_slots",
            "cheapest_hours": 8.5,
            "cheapest_hours_value": 8.5,
            "price_trigger_value": 4.2,
            "time_slots": 3,
            "time_slots_value": 3,
            "uses_tariffs_value": True,
            "tariffs": {
                hour: "on" if hour == 8 else ""
                for hour in range(24)
            },
            "schedule": calculated["schedule"],
            "tomorrow_schedule": [],
            "child_lock_value": False,
            "country_area": "finland-fi1_15m",
            "is_on": True,
            "current_price": 2.5,
            "current_period": "08:00–08:15",
            "next_change": None,
        }

        self.assertEqual(result, expected)

    def test_build_coordinator_data_missing_values(self):
        build_data = load_function(
            "_build_coordinator_data"
        )

        device = {}

        metadata = {
            "product_key": "test-device",
            "device_model": None,
            "firmware_version": None,
            "capabilities": [],
            "country_area": "finland-fi1_15m",
        }

        settings = {
            "mode": "",
            "cheapest_hours": 0.0,
            "time_slots": 1,
        }

        calculated = {
            "schedule": [],
            "tomorrow_schedule": [],
            "current": {
                "is_on": False,
                "price": 0,
            },
            "current_period": None,
            "next_change": None,
        }

        result = build_data(
            device,
            metadata,
            settings,
            calculated,
        )

        self.assertEqual(result["device_name"], "PowerAnt")
        self.assertIsNone(result["cheapest_hours_value"])
        self.assertIsNone(result["price_trigger_value"])
        self.assertIsNone(result["time_slots_value"])
        self.assertIsNone(result["uses_tariffs_value"])
        self.assertIsNone(result["child_lock_value"])

        self.assertEqual(
            result["tariffs"],
            {hour: "" for hour in range(24)},
        )

        self.assertIs(result["device"], device)
        self.assertIs(result["schedule"], calculated["schedule"])
        self.assertIs(
            result["tomorrow_schedule"],
            calculated["tomorrow_schedule"],
        )
