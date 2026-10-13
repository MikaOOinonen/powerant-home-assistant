"""Tests for PowerAnt price timestamp keys."""

import ast
import unittest
from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
    / "prices.py"
)

tree = ast.parse(SOURCE.read_text())

function = next(
    node for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_is_price_key"
)

namespace = {}
exec(
    compile(
        ast.Module(body=[function], type_ignores=[]),
        str(SOURCE),
        "exec",
    ),
    namespace,
)

_is_price_key = namespace["_is_price_key"]


class TestPriceKey(unittest.TestCase):

    def test_hourly_price_key(self):
        self.assertTrue(_is_price_key("2026101308"))

    def test_15_minute_price_key(self):
        self.assertTrue(_is_price_key("202610130815"))

    def test_invalid_price_keys(self):
        for key in (
            "",
            "20261013",
            "20261013080000",
            "2026101308AB",
            None,
            2026101308,
        ):
            with self.subTest(key=key):
                self.assertFalse(_is_price_key(key))
