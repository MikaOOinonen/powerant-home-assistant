"""Tests for PowerAnt coordinator setting updates."""

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "powerant_api"
    / "coordinator.py"
)


def load_method(name):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

    coordinator = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "PowerAntCoordinator"
    )

    method = next(
        node
        for node in coordinator.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == name
    )

    module = ast.Module(
        body=[method],
        type_ignores=[],
    )

    namespace = {}
    exec(compile(module, str(SOURCE), "exec"), namespace)

    return namespace[name]


def attach_update_setting(coordinator):
    """Attach the real update helper to the test coordinator."""

    helper = load_method("_async_update_setting")

    coordinator._async_update_setting = (
        lambda api_key, data_key, value:
        helper(coordinator, api_key, data_key, value)
    )


class TestCoordinatorSettings(unittest.IsolatedAsyncioTestCase):

    async def test_cheapest_hours_success(self):
        method = load_method("async_set_cheapest_hours")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"cheapest_hours_value": 8},
            api=SimpleNamespace(
                async_update_device=AsyncMock(),
            ),
            async_update_listeners=Mock(),
            async_request_refresh=AsyncMock(),
        )

        attach_update_setting(coordinator)
        await method(coordinator, 6.25)

        self.assertEqual(
            coordinator.data["cheapest_hours_value"],
            6.25,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"cheapest_hours": 6.25},
        )

        coordinator.async_update_listeners.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_cheapest_hours_api_failure(self):
        method = load_method("async_set_cheapest_hours")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"cheapest_hours_value": 8},
            api=SimpleNamespace(
                async_update_device=AsyncMock(
                    side_effect=RuntimeError("API failure")
                ),
            ),
            async_update_listeners=Mock(),
            async_request_refresh=AsyncMock(),
        )

        attach_update_setting(coordinator)

        with self.assertRaisesRegex(
            RuntimeError,
            "API failure",
        ):
            await method(coordinator, 6.25)

        # Original value must be restored.
        self.assertEqual(
            coordinator.data["cheapest_hours_value"],
            8,
        )

        # One notification for the new value,
        # another for the restored value.
        self.assertEqual(
            coordinator.async_update_listeners.call_count,
            2,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"cheapest_hours": 6.25},
        )

        # Refresh must not run after an API failure.
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_price_trigger_success(self):
        method = load_method("async_set_price_trigger")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"price_trigger_value": 4},
            api=SimpleNamespace(
                async_update_device=AsyncMock(),
            ),
            async_update_listeners=Mock(),
            async_request_refresh=AsyncMock(),
        )

        attach_update_setting(coordinator)
        await method(coordinator, 3.5)

        self.assertEqual(
            coordinator.data["price_trigger_value"],
            3.5,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"price_trigger": 3.5},
        )

        coordinator.async_update_listeners.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_price_trigger_api_failure(self):
        method = load_method("async_set_price_trigger")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"price_trigger_value": 4},
            api=SimpleNamespace(
                async_update_device=AsyncMock(
                    side_effect=RuntimeError("API failure")
                ),
            ),
            async_update_listeners=Mock(),
            async_request_refresh=AsyncMock(),
        )

        attach_update_setting(coordinator)

        with self.assertRaisesRegex(
            RuntimeError,
            "API failure",
        ):
            await method(coordinator, 3.5)

        self.assertEqual(
            coordinator.data["price_trigger_value"],
            4,
        )

        self.assertEqual(
            coordinator.async_update_listeners.call_count,
            2,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"price_trigger": 3.5},
        )

        coordinator.async_request_refresh.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
