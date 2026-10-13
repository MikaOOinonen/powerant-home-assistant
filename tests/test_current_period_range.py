"""Tests for current PowerAnt price period range."""

import ast
from datetime import datetime, timedelta
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
    / "prices.py"
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

    namespace = {
        "datetime": datetime,
        "timedelta": timedelta,
    }

    exec(compile(module, str(SOURCE), "exec"), namespace)

    return namespace[name]


class TestCurrentPeriodRange(unittest.TestCase):

    def test_15_minute_period(self):
        get_range = load_function(
            "_get_current_period_range"
        )

        result = get_range(
            "202610131415",
            "%Y%m%d%H%M",
            15,
        )

        self.assertEqual(result, "14:15-14:30")

    def test_60_minute_period(self):
        get_range = load_function(
            "_get_current_period_range"
        )

        result = get_range(
            "2026101314",
            "%Y%m%d%H",
            60,
        )

        self.assertEqual(result, "14:00-15:00")

    def test_period_crosses_midnight(self):
        get_range = load_function(
            "_get_current_period_range"
        )

        result = get_range(
            "202610132345",
            "%Y%m%d%H%M",
            15,
        )

        self.assertEqual(result, "23:45-00:00")


if __name__ == "__main__":
    unittest.main()
