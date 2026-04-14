#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test and control Home Assistant light brightness for ``light.bed_light``.

This script reads Home Assistant credentials from ``home_assistant.secrets.env``
in the repo root (no shell ``source`` required), then calls Home Assistant REST:

- ``POST /api/services/light/turn_on`` (with ``brightness`` 0..255)
- ``POST /api/services/light/turn_off``
- ``GET  /api/states/light.bed_light``

Usage:
  python control_bed_light_brightness.py set 128
  python control_bed_light_brightness.py on --brightness 200
  python control_bed_light_brightness.py off
  python control_bed_light_brightness.py state
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent
EXPORT_LINE = re.compile(r"^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")
DEFAULT_ENTITY_ID = "light.bed_light"


def load_env_file():
    env_path = Path(
        os.environ.get("HOME_ASSISTANT_SECRETS_PATH", str(REPO_ROOT / "home_assistant.secrets.env"))
    ).expanduser()
    if not env_path.is_file():
        return
    text = env_path.read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = EXPORT_LINE.match(line)
        if not m:
            continue
        key, raw_val = m.group(1), m.group(2).strip()
        if raw_val[:1] in "\"'" and len(raw_val) >= 2 and raw_val[-1:] == raw_val[:1]:
            raw_val = raw_val[1:-1]
        if not raw_val or "PASTE_YOUR_" in raw_val:
            continue
        if not key.startswith(("HOME_ASSISTANT", "HOMEASSISTANT")):
            continue
        if os.environ.get(key, "").strip():
            continue
        os.environ[key] = raw_val


def ha_creds():
    ip = (os.environ.get("HOME_ASSISTANT_IP", "").strip()
          or os.environ.get("HOMEASSISTANT_TEST_IP", "").strip())
    token = (os.environ.get("HOME_ASSISTANT_TOKEN", "").strip()
             or os.environ.get("HOMEASSISTANT_ACCESS_TOKEN", "").strip())
    port = (os.environ.get("HOME_ASSISTANT_PORT", "").strip()
            or os.environ.get("HOMEASSISTANT_PORT", "").strip()
            or "8123")
    if not ip or not token:
        raise ValueError(
            "Missing HOME_ASSISTANT_IP/HOME_ASSISTANT_TOKEN (check home_assistant.secrets.env)."
        )
    return ip, token, port


def request_json(method, url, token, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        },
    )
    with urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def get_state(base_url, token, entity_id):
    return request_json("GET", "{}/states/{}".format(base_url, entity_id), token)


def set_on(base_url, token, entity_id, brightness=None):
    payload = {"entity_id": entity_id}
    if brightness is not None:
        payload["brightness"] = brightness
    return request_json("POST", "{}/services/light/turn_on".format(base_url), token, payload)


def set_off(base_url, token, entity_id):
    return request_json("POST", "{}/services/light/turn_off".format(base_url), token, {"entity_id": entity_id})


def main():
    load_env_file()
    parser = argparse.ArgumentParser(description="Control Home Assistant light brightness.")
    parser.add_argument("command", choices=("set", "on", "off", "state"))
    parser.add_argument("value", nargs="?", help="Brightness value for 'set' command (0-255).")
    parser.add_argument("--brightness", type=int, default=None, help="Brightness for 'on' command (0-255).")
    parser.add_argument("--entity-id", default=DEFAULT_ENTITY_ID, help="Home Assistant light entity id.")
    args = parser.parse_args()

    if args.command == "set":
        if args.value is None:
            parser.error("set requires brightness value (0-255)")
        try:
            brightness = int(args.value)
        except ValueError:
            parser.error("brightness must be integer 0-255")
    elif args.command == "on":
        brightness = args.brightness
    else:
        brightness = None

    if brightness is not None and not (0 <= brightness <= 255):
        parser.error("brightness must be in range 0..255")

    try:
        ip, token, port = ha_creds()
        base_url = "http://{}:{}/api".format(ip, port)
        if args.command == "state":
            state = get_state(base_url, token, args.entity_id)
            attrs = state.get("attributes", {})
            print(
                "state={}, brightness={}".format(
                    state.get("state", "unknown"),
                    attrs.get("brightness", "n/a"),
                )
            )
            return 0

        if args.command == "off":
            set_off(base_url, token, args.entity_id)
            print("ok: turned off {}".format(args.entity_id))
            return 0

        set_on(base_url, token, args.entity_id, brightness=brightness)
        if brightness is None:
            print("ok: turned on {}".format(args.entity_id))
        else:
            print("ok: set {} brightness={}".format(args.entity_id, brightness))
        return 0
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print("HTTP {}: {}".format(exc.code, body), file=sys.stderr)
        return 1
    except URLError as exc:
        print("Request failed: {}".format(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
