# -*- coding: utf-8 -*- {{{
# ===----------------------------------------------------------------------===
#
#                 Component of Eclipse VOLTTRON
#
# ===----------------------------------------------------------------------===
# }}}

import pytest

from platform_driver.interfaces import home_assistant

# Do not override mock driver_config with repo-root home_assistant.secrets.env
pytestmark = pytest.mark.usefixtures("ignore_ha_secrets_file")


@pytest.fixture
def ignore_ha_secrets_file(monkeypatch):
    monkeypatch.setenv("HOME_ASSISTANT_IGNORE_SECRETS_FILE", "1")


def _build_interface(registry_config):
    interface = home_assistant.Interface()
    interface.configure(
        {
            "ip_address": "127.0.0.1",
            "access_token": "fake-token",
            "port": "8123",
        },
        registry_config,
    )
    return interface


@pytest.mark.driver_unit
@pytest.mark.parametrize(
    "set_value, expected_service",
    [
        (1, "turn_on"),
        (0, "turn_off"),
    ],
)
def test_switch_set_point_calls_expected_service(monkeypatch, set_value, expected_service):
    calls = []

    def fake_post(url, headers, data, operation_description):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "data": data,
                "operation_description": operation_description,
            }
        )

    monkeypatch.setattr(home_assistant, "_post_method", fake_post)

    interface = _build_interface(
        [
            {
                "Entity ID": "switch.bedroom_switch",
                "Entity Point": "state",
                "Volttron Point Name": "switch_state",
                "Units": "On / Off",
                "Writable": True,
                "Type": "int",
                "Notes": "mock switch state point",
            }
        ]
    )

    result = interface._set_point("switch_state", set_value)

    assert result == set_value
    assert len(calls) == 1
    assert calls[0]["url"].endswith(f"/api/services/switch/{expected_service}")
    assert calls[0]["data"]["entity_id"] == "switch.bedroom_switch"


@pytest.mark.driver_unit
@pytest.mark.parametrize(
    "bad_value, expected_error",
    [
        (2, ValueError),
        (-1, ValueError),
        ("on", ValueError),
        (None, TypeError),
    ],
)
def test_switch_set_point_rejects_invalid_state(monkeypatch, bad_value, expected_error):
    calls = []

    def fake_post(url, headers, data, operation_description):
        calls.append(url)

    monkeypatch.setattr(home_assistant, "_post_method", fake_post)

    interface = _build_interface(
        [
            {
                "Entity ID": "switch.bedroom_switch",
                "Entity Point": "state",
                "Volttron Point Name": "switch_state",
                "Units": "On / Off",
                "Writable": True,
                "Type": "int",
                "Notes": "mock switch state point",
            }
        ]
    )

    with pytest.raises(expected_error):
        interface._set_point("switch_state", bad_value)

    assert calls == []


@pytest.mark.driver_unit
def test_switch_rejects_non_state_point(monkeypatch):
    calls = []

    def fake_post(url, headers, data, operation_description):
        calls.append(url)

    monkeypatch.setattr(home_assistant, "_post_method", fake_post)

    interface = _build_interface(
        [
            {
                "Entity ID": "switch.bedroom_switch",
                "Entity Point": "brightness",
                "Volttron Point Name": "switch_brightness",
                "Units": "int",
                "Writable": True,
                "Type": "int",
                "Notes": "invalid switch point for write path",
            }
        ]
    )

    with pytest.raises(ValueError):
        interface._set_point("switch_brightness", 1)

    assert calls == []


@pytest.mark.driver_unit
def test_configure_resolves_env_placeholders(monkeypatch):
    monkeypatch.setenv("HA_UNITTEST_IP", "10.0.0.1")
    monkeypatch.setenv("HA_UNITTEST_TOKEN", "secret-token")
    monkeypatch.setenv("HA_UNITTEST_PORT", "8123")
    iface = home_assistant.Interface()
    iface.configure(
        {
            "ip_address": "${HA_UNITTEST_IP}",
            "access_token": "${HA_UNITTEST_TOKEN}",
            "port": "${HA_UNITTEST_PORT}",
        },
        [],
    )
    assert iface.ip_address == "10.0.0.1"
    assert iface.access_token == "secret-token"
    assert iface.port == "8123"


@pytest.mark.driver_unit
def test_configure_env_placeholder_missing_raises(monkeypatch):
    monkeypatch.delenv("HA_MISSING_TOKEN", raising=False)
    iface = home_assistant.Interface()
    with pytest.raises(ValueError, match="HA_MISSING_TOKEN"):
        iface.configure(
            {
                "ip_address": "127.0.0.1",
                "access_token": "${HA_MISSING_TOKEN}",
                "port": "8123",
            },
            [],
        )


@pytest.mark.driver_unit
def test_registry_entity_id_env_expansion(monkeypatch):
    monkeypatch.setenv("HOME_ASSISTANT_VOLTTRONTEST_ENTITY", "input_boolean.actual_helper")
    iface = home_assistant.Interface()
    iface.configure(
        {
            "ip_address": "127.0.0.1",
            "access_token": "fake-token",
            "port": "8123",
        },
        [
            {
                "Entity ID": "${HOME_ASSISTANT_VOLTTRONTEST_ENTITY}",
                "Entity Point": "state",
                "Volttron Point Name": "bool_state",
                "Units": "On / Off",
                "Writable": True,
                "Type": "int",
            }
        ],
    )
    assert iface.get_register_by_name("bool_state").entity_id == "input_boolean.actual_helper"
