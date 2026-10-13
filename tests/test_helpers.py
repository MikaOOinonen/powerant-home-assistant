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

function = next(
    node for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_as_bool_or_none"
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

_as_bool_or_none = namespace["_as_bool_or_none"]


class TestBooleanHelper(unittest.TestCase):

    def test_true(self):
        self.assertIs(_as_bool_or_none(True), True)

    def test_false(self):
        self.assertIs(_as_bool_or_none(False), False)

    def test_invalid_values(self):
        for value in (None, "", "true", "false", 0, 1):
            with self.subTest(value=value):
                self.assertIsNone(_as_bool_or_none(value))
