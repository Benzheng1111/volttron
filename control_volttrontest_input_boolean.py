#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Control ``input_boolean.volttrontest`` using config files only (no shell ``source``).

Reads (in order of precedence: CLI flags > environment > JSON > defaults):

1. ``home_assistant.secrets.env`` — ``HOME_ASSISTANT_IP``, ``HOME_ASSISTANT_TOKEN``,
   ``HOME_ASSISTANT_PORT`` (and optional ``VOLTTRON_DEVICE_PATH`` / ``VOLTTRON_POINT_NAME``
   if you put them there).
2. ``examples/home-assistant/volttrontest_cli.json`` — ``backend``, ``entity_id``,
   ``volttron.device_path``, ``volttron.point_name``.

Override file paths::

  HOME_ASSISTANT_SECRETS_PATH
  VOLTTRON_CLI_CONFIG

Usage::

  python control_volttrontest_input_boolean.py on
  python control_volttrontest_input_boolean.py off
  python control_volttrontest_input_boolean.py state

  # Skip VOLTTRON; call Home Assistant HTTP API (set \"backend\": \"ha_rest\" in JSON or use --via-ha)
  python control_volttrontest_input_boolean.py on --via-ha
"""
import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path

import gevent

from volttron.platform.agent import utils
from volttron.platform.agent.known_identities import PLATFORM_DRIVER
from volttron.platform.vip.agent import Agent

_REPO_ROOT = Path(__file__).resolve().parent
_DEFAULT_CLI_CONFIG = _REPO_ROOT / "examples/home-assistant/volttrontest_cli.json"
_EXPORT_LINE = re.compile(
    r"^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$"
)


def _load_export_env_file(path):
    """Parse ``export KEY=value`` lines into os.environ (do not override existing)."""
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print("Warning: could not read {}: {}".format(path, exc), file=sys.stderr)
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _EXPORT_LINE.match(line)
        if not m:
            continue
        key, raw_val = m.group(1), m.group(2).strip()
        if raw_val[:1] in "\"'" and len(raw_val) >= 2 and raw_val[-1:] == raw_val[:1]:
            raw_val = raw_val[1:-1]
        if not raw_val or "PASTE_YOUR_" in raw_val:
            continue
        if not (
            key.startswith("HOME_ASSISTANT")
            or key.startswith("HOMEASSISTANT")
            or key.startswith("VOLTTRON_")
        ):
            continue
        if os.environ.get(key, "").strip():
            continue
        os.environ[key] = raw_val


def _load_cli_json(path):
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print("Warning: could not read {}: {}".format(path, exc), file=sys.stderr)
        return {}


def _ha_credentials():
    ip = (
        os.environ.get("HOME_ASSISTANT_IP", "").strip()
        or os.environ.get("HOMEASSISTANT_TEST_IP", "").strip()
    )
    token = (
        os.environ.get("HOME_ASSISTANT_TOKEN", "").strip()
        or os.environ.get("HOMEASSISTANT_ACCESS_TOKEN", "").strip()
    )
    port = (
        os.environ.get("HOME_ASSISTANT_PORT", "").strip()
        or os.environ.get("HOMEASSISTANT_PORT", "").strip()
        or "8123"
    )
    return ip, token, port


def _ha_rest(command, entity_id):
    try:
        from urllib.error import HTTPError, URLError
        from urllib.request import Request, urlopen
    except ImportError:
        print("urllib is required for --via-ha", file=sys.stderr)
        return 1

    ip, token, port = _ha_credentials()
    if not ip or not token:
        print(
            "HOME_ASSISTANT_IP and HOME_ASSISTANT_TOKEN must be set (e.g. in home_assistant.secrets.env).",
            file=sys.stderr,
        )
        return 1

    base = "http://{}:{}/api".format(ip, port)
    headers = {
        "Authorization": "Bearer {}".format(token),
        "Content-Type": "application/json",
    }

    def _request(method, url, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8"), resp.status
        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print("HTTP {}: {}".format(e.code, err_body), file=sys.stderr)
            raise
        except URLError as e:
            print("Request failed: {}".format(e), file=sys.stderr)
            raise

    try:
        if command == "state":
            url = "{}/states/{}".format(base, entity_id)
            raw, _ = _request("GET", url)
            st = json.loads(raw).get("state", "")
            print(1 if st == "on" else 0)
        elif command == "on":
            url = "{}/services/input_boolean/turn_on".format(base)
            _request("POST", url, {"entity_id": entity_id})
            print("ok (turn_on)")
        else:
            url = "{}/services/input_boolean/turn_off".format(base)
            _request("POST", url, {"entity_id": entity_id})
            print("ok (turn_off)")
    except Exception:
        return 1
    return 0


def _wait_connected(core, timeout_s):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if core.connected:
            return True
        gevent.sleep(0.2)
    return False


def _run_volttron(command, device_path, point_name):
    utils.setup_logging(level=logging.WARNING)
    identity = "cli.control_volttrontest.{}".format(uuid.uuid4().hex[:12])
    cli = Agent(
        identity=identity,
        enable_auth=False,
        enable_store=False,
        heartbeat_autostart=False,
    )
    glt = gevent.spawn(cli.core.run)

    print("Connecting to VIP (max 25s)...", file=sys.stderr)
    if not _wait_connected(cli.core, timeout_s=25):
        print(
            "VIP did not connect within 25s.\n"
            "Check: volttron running, ~/.volttron/run/vip.socket exists;\n"
            "for dev set allow-auth = false under [volttron] in ~/.volttron/config and restart.",
            file=sys.stderr,
        )
        cli.core.stop()
        glt.join(timeout=10)
        return 1

    try:
        if command == "state":
            res = cli.vip.rpc.call(
                PLATFORM_DRIVER,
                "get_point",
                device_path,
                point_name,
            ).get(timeout=60)
            print(res)
        elif command == "on":
            res = cli.vip.rpc.call(
                PLATFORM_DRIVER,
                "set_point",
                device_path,
                point_name,
                1,
            ).get(timeout=60)
            print("set_point result:", res)
        else:
            res = cli.vip.rpc.call(
                PLATFORM_DRIVER,
                "set_point",
                device_path,
                point_name,
                0,
            ).get(timeout=60)
            print("set_point result:", res)
    finally:
        cli.core.stop()
        glt.join(timeout=15)
    return 0


def main():
    secrets_path = Path(
        os.environ.get("HOME_ASSISTANT_SECRETS_PATH", str(_REPO_ROOT / "home_assistant.secrets.env"))
    ).expanduser()
    _load_export_env_file(secrets_path)

    cli_config_path = Path(
        os.environ.get("VOLTTRON_CLI_CONFIG", str(_DEFAULT_CLI_CONFIG))
    ).expanduser()
    file_cfg = _load_cli_json(cli_config_path)
    vt = file_cfg.get("volttron") or {}
    entity_id = file_cfg.get("entity_id", "input_boolean.volttrontest")
    default_backend = (file_cfg.get("backend") or "volttron").strip().lower()

    parser = argparse.ArgumentParser(
        description="Control input_boolean helper: load secrets + volttrontest_cli.json, then act."
    )
    parser.add_argument("command", choices=("on", "off", "state"))
    parser.add_argument(
        "--config",
        default=None,
        help="Path to volttrontest_cli.json (default: examples/home-assistant/volttrontest_cli.json or VOLTTRON_CLI_CONFIG).",
    )
    parser.add_argument(
        "--device-path",
        default=None,
        help="Override volttron device_path (config store path without devices/).",
    )
    parser.add_argument(
        "--point",
        default=None,
        help="Override Volttron point name (default bool_state).",
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--via-ha",
        action="store_true",
        help="Call Home Assistant REST API (needs IP/token in secrets); no Platform Driver.",
    )
    g.add_argument(
        "--via-volttron",
        action="store_true",
        help="Force platform.driver RPC even if JSON backend is ha_rest.",
    )
    args = parser.parse_args()

    if args.config:
        file_cfg = _load_cli_json(Path(args.config).expanduser())
        vt = file_cfg.get("volttron") or {}
        entity_id = file_cfg.get("entity_id", entity_id)
        default_backend = (file_cfg.get("backend") or default_backend).strip().lower()

    device_path = (
        args.device_path
        or os.environ.get("VOLTTRON_DEVICE_PATH", "").strip()
        or vt.get("device_path")
        or "demo/site/room/volttrontest"
    )
    point_name = (
        args.point
        or os.environ.get("VOLTTRON_POINT_NAME", "").strip()
        or vt.get("point_name")
        or "bool_state"
    )

    if args.via_ha:
        backend = "ha_rest"
    elif args.via_volttron:
        backend = "volttron"
    else:
        backend = default_backend if default_backend in ("volttron", "ha_rest") else "volttron"

    if backend == "ha_rest":
        return _ha_rest(args.command, entity_id)
    return _run_volttron(args.command, device_path, point_name)


if __name__ == "__main__":
    sys.exit(main())
