"""Tests for shared PowerAnt helper functions."""

import ast
import unittest
from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
    / "helpers.py"
)

tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

functions = [
    node for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name in (
        "_as_bool_or_none",
        "_as_float_or_none",
        "_as_int_or_none",
    )
]

namespace = {}

exec(
    compile(
        ast.Module(body=functions, type_ignores=[]),
        str(SOURCE),
        "exec",
    ),
    namespace,
)

_as_bool_or_none = namespace["_as_bool_or_none"]
_as_float_or_none = namespace["_as_float_or_none"]
_as_int_or_none = namespace["_as_int_or_none"]


class TestBooleanHelper(unittest.TestCase):

    def test_true(self):
        self.assertIs(_as_bool_or_none(True), True)

    def test_false(self):
        self.assertIs(_as_bool_or_none(False), False)

    def test_invalid_values(self):
        for value in (None, "", "true", "false", 0, 1):
            with self.subTest(value=value):
                self.assertIsNone(_as_bool_or_none(value))


class TestAsFloatOrNone(unittest.TestCase):
    def test_valid_numbers(self):
        self.assertEqual(_as_float_or_none(12), 12.0)
        self.assertEqual(_as_float_or_none(12.5), 12.5)
        self.assertEqual(_as_float_or_none("12.5"), 12.5)
        self.assertEqual(_as_float_or_none("-3.25"), -3.25)

    def test_empty_values(self):
        self.assertIsNone(_as_float_or_none(None))
        self.assertIsNone(_as_float_or_none(""))

    def test_invalid_values(self):
        self.assertIsNone(_as_float_or_none("invalid"))
        self.assertIsNone(_as_float_or_none([]))
        self.assertIsNone(_as_float_or_none({}))


class TestAsIntOrNone(unittest.TestCase):
    def test_valid_numbers(self):
        self.assertEqual(_as_int_or_none(12), 12)
        self.assertEqual(_as_int_or_none(12.9), 12)
        self.assertEqual(_as_int_or_none("12"), 12)
        self.assertEqual(_as_int_or_none("12.9"), 12)
        self.assertEqual(_as_int_or_none("-3.9"), -3)

    def test_empty_values(self):
        self.assertIsNone(_as_int_or_none(None))
        self.assertIsNone(_as_int_or_none(""))

    def test_invalid_values(self):
        for value in ("invalid", [], {}):
            with self.subTest(value=value):
                self.assertIsNone(_as_int_or_none(value))
