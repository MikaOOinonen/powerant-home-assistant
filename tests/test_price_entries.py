"""Tests for PowerAnt price entry calculations."""

import ast
import unittest
from pathlib import Path


BASE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
)

COORDINATOR = BASE / "coordinator.py"
PRICES = BASE / "prices.py"


def load_function(source, name, namespace):
    tree = ast.parse(source.read_text())

    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == name
    )

    exec(
        compile(
            ast.Module(
                body=[function],
                type_ignores=[],
            ),
            str(source),
            "exec",
        ),
        namespace,
    )


namespace = {}

load_function(PRICES, "_as_bool_or_none", namespace)
load_function(PRICES, "_is_price_key", namespace)
load_function(PRICES, "_build_price_entries", namespace)

_build_price_entries = namespace["_build_price_entries"]


class TestPriceEntries(unittest.TestCase):

    def test_hourly_prices(self):
        prices = {
            "2026101309": 4.0,
            "2026101308": 2.0,
        }

        entries = _build_price_entries(
            prices, {}, "20261013", False
        )

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["timestamp"], "2026101308")
        self.assertEqual(entries[0]["effective"], 2.0)
        self.assertFalse(entries[0]["is_on"])

    def test_15_minute_prices(self):
        prices = {
            "202610130800": 2.0,
            "202610130815": 3.0,
            "2026101308": 9.0,
        }

        entries = _build_price_entries(
            prices, {}, "20261013", True
        )

        self.assertEqual(len(entries), 2)
        self.assertEqual(
            [e["timestamp"] for e in entries],
            ["202610130800", "202610130815"],
        )

    def test_forced_on(self):
        device = {
            "uses_tariffs": True,
            "tariff_8": "ON",
        }

        entries = _build_price_entries(
            {"2026101308": 5.0},
            device, "20261013", False
        )

        self.assertEqual(entries[0]["rule"], "ON")
        self.assertEqual(entries[0]["effective"], 5.0)

    def test_forced_off(self):
        device = {
            "uses_tariffs": True,
            "tariff_8": "OFF",
        }

        entries = _build_price_entries(
            {"2026101308": 5.0},
            device, "20261013", False
        )

        self.assertEqual(entries[0]["rule"], "OFF")

    def test_numeric_tariff(self):
        device = {
            "uses_tariffs": True,
            "tariff_8": "1.5",
        }

        entries = _build_price_entries(
            {"2026101308": 5.0},
            device, "20261013", False
        )

        self.assertEqual(entries[0]["tariff"], 1.5)
        self.assertEqual(entries[0]["effective"], 6.5)
        self.assertEqual(entries[0]["rule"], "+1.5")

    def test_tariffs_disabled(self):
        device = {
            "uses_tariffs": False,
            "tariff_8": "ON",
        }

        entries = _build_price_entries(
            {"2026101308": 5.0},
            device, "20261013", False
        )

        self.assertEqual(entries[0]["rule"], "-")
        self.assertEqual(entries[0]["effective"], 5.0)
