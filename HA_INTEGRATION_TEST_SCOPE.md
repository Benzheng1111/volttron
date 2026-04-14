# Home Assistant Integration Test Scope

This document describes what is validated by:
`services/core/PlatformDriverAgent/tests/test_home_assistant.py`.

## Goal

Validate end-to-end behavior between Volttron PlatformDriver and a real Home Assistant instance.

## Environment Requirements

- Running Home Assistant instance
- **One credentials file at the repository root** (gitignored):
  - Copy `home_assistant.secrets.env.example` → `home_assistant.secrets.env`
  - Paste **IP/hostname and token once** in that file; it also sets the names used by pytest (`HOMEASSISTANT_TEST_IP`, `HOMEASSISTANT_ACCESS_TOKEN`, `HOMEASSISTANT_PORT`).

Load before `pytest`:

```bash
cd /path/to/volttron
set -a && source home_assistant.secrets.env && set +a
pytest services/core/PlatformDriverAgent/tests/test_home_assistant.py
```

Or from any directory:

```bash
set -a && source /path/to/volttron/services/core/PlatformDriverAgent/tests/load_home_assistant_secrets.env && set +a
pytest /path/to/volttron/services/core/PlatformDriverAgent/tests/test_home_assistant.py
```

- Helper toggle created in Home Assistant:
  - `input_boolean.volttrontest`

If required variables are empty, tests are skipped by design.

## What The Test Validates

### 1) `test_get_point`

- Calls PlatformDriver RPC:
  - `get_point("home_assistant", "bool_state")`
- Validates read path from Home Assistant entity state through Volttron.

### 2) `test_data_poll`

- Calls PlatformDriver RPC:
  - `scrape_all("home_assistant")`
- Validates periodic read/polling path and expected mapped values.

### 3) `test_set_point`

- Calls PlatformDriver RPC:
  - `set_point("home_assistant", "bool_state", 1)`
- Then polls with `scrape_all(...)` to verify write effect is observed.

## Parameterized Fixture Behavior

The file runs each test under 3 fixture variants:

- `volttron_instance0`: ZMQ default auth (primary expected pass path)
- `volttron_instance1`: RMQ + SSL auth (often skipped if RMQ unavailable)
- `volttron_instance2`: ZMQ with auth disabled (may fail in some environments)

For local sprint validation, the common command is to focus on instance0:

```bash
./env/bin/python -m pytest -vv -k "volttron_instance0" services/core/PlatformDriverAgent/tests/test_home_assistant.py
```

## What This File Does Not Validate

- Fine-grained unit behavior for every helper method
- Offline behavior with mocked API
- Exhaustive domain coverage beyond configured entities
