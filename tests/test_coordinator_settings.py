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

    const_source = SOURCE.with_name("const.py")
    const_tree = ast.parse(
        const_source.read_text(encoding="utf-8")
    )

    modes_node = next(
        node
        for node in const_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "POWERANT_MODES"
            for target in node.targets
        )
    )

    namespace = {
        "POWERANT_MODES": ast.literal_eval(
            modes_node.value
        ),
    }

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

    async def test_country_area_success(self):
        method = load_method("async_set_country_area")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"country_area": "finland-fi1"},
            api=SimpleNamespace(
                async_update_device=AsyncMock(),
            ),
            async_update_listeners=Mock(),
            async_request_refresh=AsyncMock(),
        )

        attach_update_setting(coordinator)
        await method(coordinator, "finland-fi1_15m")

        self.assertEqual(
            coordinator.data["country_area"],
            "finland-fi1_15m",
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"country_area": "finland-fi1_15m"},
        )

        coordinator.async_update_listeners.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_uses_tariffs_success(self):
        method = load_method("async_set_uses_tariffs")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"uses_tariffs_value": False},
            api=SimpleNamespace(
                async_update_device=AsyncMock(),
            ),
            async_update_listeners=Mock(),
            async_request_refresh=AsyncMock(),
        )

        attach_update_setting(coordinator)
        await method(coordinator, True)

        self.assertIs(
            coordinator.data["uses_tariffs_value"],
            True,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"uses_tariffs": True},
        )

        coordinator.async_update_listeners.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

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

    async def test_time_slots_success(self):
        method = load_method("async_set_time_slots")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"time_slots_value": 3},
            api=SimpleNamespace(
                async_update_device=AsyncMock(),
            ),
            async_update_listeners=Mock(),
            async_request_refresh=AsyncMock(),
        )

        attach_update_setting(coordinator)
        await method(coordinator, 4.9)

        # time_slots must always be an integer.
        self.assertEqual(
            coordinator.data["time_slots_value"],
            4,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"time_slots": 4},
        )

        coordinator.async_update_listeners.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_time_slots_api_failure(self):
        method = load_method("async_set_time_slots")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"time_slots_value": 3},
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
            await method(coordinator, 4.9)

        # Original value must be restored.
        self.assertEqual(
            coordinator.data["time_slots_value"],
            3,
        )

        # Notify once for the new value and once for rollback.
        self.assertEqual(
            coordinator.async_update_listeners.call_count,
            2,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"time_slots": 4},
        )

        # No refresh after API failure.
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_uses_tariffs_api_failure(self):
        method = load_method("async_set_uses_tariffs")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"uses_tariffs_value": False},
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
            await method(coordinator, True)

        # Original value must be restored.
        self.assertIs(
            coordinator.data["uses_tariffs_value"],
            False,
        )

        # One notification for the new value,
        # another for the restored value.
        self.assertEqual(
            coordinator.async_update_listeners.call_count,
            2,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"uses_tariffs": True},
        )

        # No refresh after API failure.
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_country_area_api_failure(self):
        method = load_method("async_set_country_area")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"country_area": "finland-fi1"},
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
            await method(coordinator, "finland-fi1_15m")

        # Original area must be restored.
        self.assertEqual(
            coordinator.data["country_area"],
            "finland-fi1",
        )

        # Notify once for the new area and once for rollback.
        self.assertEqual(
            coordinator.async_update_listeners.call_count,
            2,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"country_area": "finland-fi1_15m"},
        )

        # No refresh after API failure.
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_mode_success(self):
        method = load_method("async_set_mode")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"mode": "off"},
            api=SimpleNamespace(
                async_update_device=AsyncMock(),
            ),
            async_update_listeners=Mock(),
            async_request_refresh=AsyncMock(),
        )

        attach_update_setting(coordinator)
        await method(coordinator, "TIME_SLOTS")

        self.assertEqual(
            coordinator.data["mode"],
            "time_slots",
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"mode": "time_slots"},
        )

        coordinator.async_update_listeners.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_mode_api_failure(self):
        method = load_method("async_set_mode")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={"mode": "off"},
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
            await method(coordinator, "TIME_SLOTS")

        # Original mode must be restored.
        self.assertEqual(
            coordinator.data["mode"],
            "off",
        )

        # Notify once for the new mode and once for rollback.
        self.assertEqual(
            coordinator.async_update_listeners.call_count,
            2,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"mode": "time_slots"},
        )

        # No refresh after API failure.
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_tariff_success(self):
        method = load_method("async_set_tariff")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={
                "tariffs": {
                    8: 1.5,
                },
            },
            api=SimpleNamespace(
                async_update_device=AsyncMock(),
            ),
            async_update_listeners=Mock(),
            async_request_refresh=AsyncMock(),
        )

        await method(coordinator, 8, "2.5")

        # Numeric string must be converted to float.
        self.assertEqual(
            coordinator.data["tariffs"][8],
            2.5,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"tariff_8": 2.5},
        )

        coordinator.async_update_listeners.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_tariff_api_failure(self):
        method = load_method("async_set_tariff")

        coordinator = SimpleNamespace(
            product_key="test-device",
            data={
                "tariffs": {
                    8: 1.5,
                },
            },
            api=SimpleNamespace(
                async_update_device=AsyncMock(
                    side_effect=RuntimeError("API failure")
                ),
            ),
            async_update_listeners=Mock(),
            async_request_refresh=AsyncMock(),
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "API failure",
        ):
            await method(coordinator, 8, "2.5")

        # Original tariff must be restored.
        self.assertEqual(
            coordinator.data["tariffs"][8],
            1.5,
        )

        # Notify once for update and once for rollback.
        self.assertEqual(
            coordinator.async_update_listeners.call_count,
            2,
        )

        coordinator.api.async_update_device.assert_awaited_once_with(
            "test-device",
            {"tariff_8": 2.5},
        )

        # No refresh after API failure.
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_tariff_special_values(self):
        method = load_method("async_set_tariff")

        for value, expected in [
            ("ON", "on"),
            ("OFF", "off"),
            ("", ""),
            ("  ON  ", "on"),
        ]:
            with self.subTest(value=value):
                coordinator = SimpleNamespace(
                    product_key="test-device",
                    data={"tariffs": {}},
                    api=SimpleNamespace(
                        async_update_device=AsyncMock(),
                    ),
                    async_update_listeners=Mock(),
                    async_request_refresh=AsyncMock(),
                )

                await method(coordinator, 8, value)

                self.assertEqual(
                    coordinator.data["tariffs"][8],
                    expected,
                )

                coordinator.api.async_update_device.assert_awaited_once_with(
                    "test-device",
                    {"tariff_8": expected},
                )

                coordinator.async_update_listeners.assert_called_once()
                coordinator.async_request_refresh.assert_awaited_once()

    async def test_tariff_invalid_values(self):
        method = load_method("async_set_tariff")

        for value in ["invalid", "auto", "1.2.3"]:
            with self.subTest(value=value):
                coordinator = SimpleNamespace(
                    product_key="test-device",
                    data={"tariffs": {8: 1.5}},
                    api=SimpleNamespace(
                        async_update_device=AsyncMock(),
                    ),
                    async_update_listeners=Mock(),
                    async_request_refresh=AsyncMock(),
                )

                with self.assertRaisesRegex(
                    ValueError,
                    "Unsupported PowerAnt tariff value",
                ):
                    await method(coordinator, 8, value)

                # Original value must remain unchanged.
                self.assertEqual(
                    coordinator.data["tariffs"][8],
                    1.5,
                )

                # No API call or state notification.
                coordinator.api.async_update_device.assert_not_awaited()
                coordinator.async_update_listeners.assert_not_called()
                coordinator.async_request_refresh.assert_not_awaited()

    async def test_tariff_hour_boundaries(self):
        method = load_method("async_set_tariff")

        for hour in [0, 23, -1, 24]:
            with self.subTest(hour=hour):
                coordinator = SimpleNamespace(
                    product_key="test-device",
                    data={"tariffs": {}},
                    api=SimpleNamespace(
                        async_update_device=AsyncMock(),
                    ),
                    async_update_listeners=Mock(),
                    async_request_refresh=AsyncMock(),
                )

                if hour in (0, 23):
                    await method(coordinator, hour, "on")

                    self.assertEqual(
                        coordinator.data["tariffs"][hour],
                        "on",
                    )

                    coordinator.api.async_update_device.assert_awaited_once_with(
                        "test-device",
                        {f"tariff_{hour}": "on"},
                    )

                    coordinator.async_update_listeners.assert_called_once()
                    coordinator.async_request_refresh.assert_awaited_once()

                else:
                    with self.assertRaisesRegex(
                        ValueError,
                        "Unsupported PowerAnt tariff hour",
                    ):
                        await method(coordinator, hour, "on")

                    self.assertEqual(
                        coordinator.data["tariffs"],
                        {},
                    )

                    coordinator.api.async_update_device.assert_not_awaited()
                    coordinator.async_update_listeners.assert_not_called()
                    coordinator.async_request_refresh.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
