# Home Assistant Mock Unit Test Scope

This document describes what is validated by:
`services/core/PlatformDriverAgent/tests/test_home_assistant_mock.py`.

## Goal

Validate Home Assistant write-path logic without requiring a live Home Assistant instance.

## Test Type

- Unit tests
- Network-independent (mocked)
- Fast execution

## What Is Mocked

- `home_assistant._post_method` is monkeypatched.
- No real HTTP request is sent.
- Assertions are made on constructed service URL and payload behavior.

## Current Coverage

### 1) Switch write success path

- `switch state = 1` -> service path ends with:
  - `/api/services/switch/turn_on`
- `switch state = 0` -> service path ends with:
  - `/api/services/switch/turn_off`
- Verifies payload contains correct `entity_id`.

### 2) Switch invalid input path

- Invalid values are rejected:
  - `2`, `-1`, `"on"`, `None`
- Ensures no outbound service call is made for invalid values.

### 3) Switch unsupported point path

- `switch` with non-`state` point (example: `brightness`) is rejected.
- Ensures no outbound service call is made.

## What This File Does Not Validate

- Real Home Assistant connectivity
- Access token validity
- Live entity state changes in Home Assistant
- End-to-end Volttron agent behavior across message bus

## Run Command

```bash
./env/bin/python -m pytest -vv services/core/PlatformDriverAgent/tests/test_home_assistant_mock.py
```
