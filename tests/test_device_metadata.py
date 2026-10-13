"""Tests for PowerAnt device metadata extraction."""

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

    namespace = {}
    exec(compile(module, str(SOURCE), "exec"), namespace)

    return namespace[name]


class TestDeviceMetadata(unittest.TestCase):

    def test_normal_device_metadata(self):
        get_metadata = load_function(
            "_get_device_metadata"
        )

        device = {
            "country_area": "finland-fi1_15m",
            "expand": {
                "device_type": {
                    "device_name": "Powerant Switch 63A",
                    "version": "3.14",
                    "device_capabilities": ["switch"],
                }
            },
        }

        result = get_metadata(device)

        self.assertEqual(
            result,
            (
                "Powerant Switch 63A",
                "3.14",
                ["switch"],
                "finland-fi1_15m",
            ),
        )


if __name__ == "__main__":
    unittest.main()
