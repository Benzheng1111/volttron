# How To Add A New Home Assistant Device

This guide explains how to add support for a new Home Assistant device domain in:
`services/core/PlatformDriverAgent/platform_driver/interfaces/home_assistant.py`.

## Current Write Support

- Binary state devices (`state` with `0/1`):
  - `light.*`
  - `input_boolean.*`
  - `switch.*`
- Light-only point:
  - `brightness` (0-255)
- Climate-only points:
  - `state` (0/2/3/4 -> off/heat/cool/auto)
  - `temperature`

## Design Pattern Used

- `_set_point()` is the routing entry point.
- `_call_service(domain, service, entity_id, operation_description, payload=None)` centralizes Home Assistant API calls.
- `_set_binary_state(entity_id, value)` centralizes `0/1 -> turn_off/turn_on` behavior.

## Steps To Add A New Device

### 1) Decide if the device is binary or special

- If device uses simple `on/off` (example: `fan` power), prefer binary path.
- If device needs special payloads (example: `lock.lock`, `cover.set_cover_position`), add dedicated handler logic.

### 2) Update `_set_point()` routing

- Add a new route based on `entity_id` prefix and `entity_point`.
- Reuse `_set_binary_state()` whenever possible.

Example routing idea:

```python
if entity_id.startswith("fan.") and entity_point == "state":
    self._set_binary_state(entity_id, register.value)
```

### 3) Add any specialized service call

- Use `_call_service(...)` to avoid duplicated URL/header code.

Example:

```python
self._call_service("lock", "lock", entity_id, f"lock {entity_id}")
```

### 4) Update error messages

- Keep unsupported-domain errors up to date so users know what is currently supported.

### 5) Add tests

- Add/extend mock unit tests in:
  - `services/core/PlatformDriverAgent/tests/test_home_assistant_mock.py`
- Optionally add/extend integration tests in:
  - `services/core/PlatformDriverAgent/tests/test_home_assistant.py`

## Suggested Definition Of Done

- Existing supported devices still pass regression tests.
- New device has:
  - at least one valid write test
  - at least one invalid-input test
- Error messages are clear for unsupported points/domains.
