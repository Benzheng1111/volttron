# -*- coding: utf-8 -*-
# ===----------------------------------------------------------------------===
#
#                 Component of Eclipse VOLTTRON
#
# ===----------------------------------------------------------------------===
#
# Copyright 2023 Battelle Memorial Institute
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# ===----------------------------------------------------------------------===
# }}}

"""Minimal agent: RPC to platform.driver set_point/get_point for a boolean point.

Install (from repo root, with VOLTTRON running)::

    vctl install examples/home-assistant/HaSwitchAgent \\
        --tag ha_switch --start

``--tag`` is only a label for ``vctl status`` / ``vctl remove``. The VIP peer
name used by ``vctl rpc call`` comes from ``--vip-identity`` or the ``IDENTITY``
file in this directory (default ``ha_switch``). ``--tag ha_switch`` alone does
**not** set the peer name to ``ha_switch``.

List methods, print sample Python, or call RPC from the shell::

    vctl rpc list ha_switch
    vctl rpc code ha_switch turn_on
    vctl rpc call ha_switch turn_on

Invoke the agent without ``vctl`` (same idea as ``turn_on_volttrontest.py``)::

    python examples/home-assistant/HaSwitchAgent/call_ha_switch.py on
    python examples/home-assistant/HaSwitchAgent/call_ha_switch.py off
    python examples/home-assistant/HaSwitchAgent/call_ha_switch.py state

Edit ``config`` to change ``device_path`` / ``point_name`` for other devices.

``turn_on`` / ``turn_off`` / ``get_state`` use ``ha_switch_agent.driver_rpc`` —
the same ``platform.driver`` ``set_point`` / ``get_point`` sequence as
``turn_on_volttrontest.py``.
"""
import logging
import sys

from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, RPC

from ha_switch_agent.driver_rpc import (
    DEFAULT_DEVICE_PATH,
    DEFAULT_POINT_NAME,
    driver_get_point,
    driver_set_point,
)

utils.setup_logging()
_log = logging.getLogger(__name__)
__version__ = '1.0'

DEFAULT_RPC_TIMEOUT = 30


class HaSwitchAgent(Agent):
    """RPC facade for a single driver boolean point (e.g. Home Assistant switch)."""

    def __init__(self, config_path, **kwargs):
        super(HaSwitchAgent, self).__init__(**kwargs)
        self.config = utils.load_config(config_path)
        self._device_path = self.config.get('device_path', DEFAULT_DEVICE_PATH)
        self._point_name = self.config.get('point_name', DEFAULT_POINT_NAME)
        self._timeout = int(self.config.get('rpc_timeout', DEFAULT_RPC_TIMEOUT))
        _log.info(
            'HaSwitchAgent device_path=%r point_name=%r',
            self._device_path,
            self._point_name,
        )

    def _set_point(self, value):
        # Same code path as turn_on_volttrontest.py (via driver_rpc helpers).
        return driver_set_point(
            self.vip, self._device_path, self._point_name, value, self._timeout
        )

    @RPC.export
    def turn_on(self):
        """Set the configured point to 1 (on)."""
        return self._set_point(1)

    @RPC.export
    def turn_off(self):
        """Set the configured point to 0 (off)."""
        return self._set_point(0)

    @RPC.export
    def get_state(self):
        """Read the current value of the configured point."""
        return driver_get_point(
            self.vip, self._device_path, self._point_name, self._timeout
        )


def main(argv=sys.argv):
    utils.vip_main(HaSwitchAgent)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
