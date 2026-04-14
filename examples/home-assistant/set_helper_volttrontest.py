"""
CLI: set ``input_boolean.volttrontest`` via ``platform.driver`` ``set_point`` (VIP).

Prerequisites: VOLTTRON + platform.driver running; registry + device loaded (see below).
Dev: ``allow-auth = false`` under ``[volttron]`` in ``~/.volttron/config``, restart platform.

Usage (repo root, ``source env/bin/activate``):

  python examples/home-assistant/set_helper_volttrontest.py 1   # on
  python examples/home-assistant/set_helper_volttrontest.py 0   # off
"""
import sys
import time
import uuid

import gevent

from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent

DEVICE_RPC_PATH = "demo/site/room/volttrontest"
POINT_NAME = "bool_state"


def _wait_connected(core, timeout_s):
    """ZMQ Core only sets ``connected`` after successful VIP hello."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if core.connected:
            return True
        gevent.sleep(0.2)
    return False


def main():
    try:
        value = int(sys.argv[1])
    except (IndexError, ValueError):
        print("Usage: python set_helper_volttrontest.py 0|1", file=sys.stderr)
        sys.exit(1)
    if value not in (0, 1):
        print("Value must be 0 or 1", file=sys.stderr)
        sys.exit(1)

    utils.setup_logging()

    server = Agent(
        identity="cli.ha.{}".format(uuid.uuid4().hex[:12]),
        enable_auth=False,
        enable_store=False,
        heartbeat_autostart=False,
    )
    glt = gevent.spawn(server.core.run)

    if not _wait_connected(server.core, timeout_s=25):
        print(
            "VIP did not connect within 25s (hello did not complete).\n"
            "Check: (1) volttron is running, (2) ~/.volttron/run/vip.socket exists,\n"
            "      (3) for dev set allow-auth = false in ~/.volttron/config and restart platform,\n"
            "      (4) no stale duplicate agent using the same identity.",
            file=sys.stderr,
        )
        server.core.stop()
        glt.join(timeout=10)
        sys.exit(1)

    try:
        res = server.vip.rpc.call(
            "platform.driver",
            "set_point",
            DEVICE_RPC_PATH,
            POINT_NAME,
            value,
        ).get(timeout=60)
        print("set_point result:", res)
    finally:
        server.core.stop()
        glt.join(timeout=15)


if __name__ == "__main__":
    main()
