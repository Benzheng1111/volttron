.. _HomeAssistant-Customer-Guide:

Home Assistant integration — customer guide
===========================================

This page is a concise, end-user oriented guide for using VOLTTRON to **read** Home Assistant entity data and **write**
(issue control commands) where the Home Assistant driver supports it. For API details of the driver class, see
:ref:`HomeAssistant-Driver`.

What you need
-------------

* A running **Home Assistant** instance reachable from the VOLTTRON host (IP or hostname and port; default **8123**).
* A **long-lived access token** from Home Assistant (`long-lived access token
  <https://developers.home-assistant.io/docs/auth_api/#long-lived-access-token>`_).
* A running **VOLTTRON** platform.
* The **Platform Driver** agent installed and started (VIP identity ``platform.driver``).
* One **device configuration** JSON and one **registry** JSON per logical device (or group of entities), stored in the
  Platform Driver configuration store (see below).

Install the Platform Driver
---------------------------

From the VOLTTRON repository root, with the virtual environment activated:

.. code-block:: bash

   vctl install services/core/PlatformDriverAgent \
     --agent-config services/core/PlatformDriverAgent/platform-driver.agent \
     --tag platform_driver \
     --start

Confirm it is running:

.. code-block:: bash

   vctl status

You should see an agent whose identity is ``platform.driver``.

Register your Home Assistant device
-----------------------------------

Each driver instance is keyed by a **device path** of the form ``<campus>/<building>/<device_id>``. When you store
configuration under ``devices/<that path>``, the Platform Driver publishes topics such as
``devices/<campus>/<building>/<device_id>/all``.

1. **Device configuration** — JSON with ``driver_type`` set to ``home_assistant``, ``driver_config`` containing
   ``ip_address``, ``access_token``, and ``port``, and ``registry_config`` pointing at a registry file in the config
   store (for example ``"registry_config": "config://my_registry.json"``).

2. **Registry configuration** — JSON list of registers: each row maps a Home Assistant **Entity ID** and **Entity Point**
   to a **Volttron Point Name** used in RPC and on the message bus. Use Home Assistant **Developer tools** to inspect
   states and attributes.

3. **Load both into the config store** (paths are examples — use names consistent with your deployment):

.. code-block:: bash

   vctl config store platform.driver my_registry.json /path/to/my_registry.json
   vctl config store platform.driver devices/BUILDING/ZONE/my_ha_device /path/to/my_ha_device.config.json

Restart the Platform Driver if it was already running so it picks up new devices:

.. code-block:: bash

   vctl restart --tag platform_driver

What can be written (control) today
-----------------------------------

The driver maps Home Assistant entities to VOLTTRON points. **Write** support depends on entity type and **Entity Point**:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Entity prefix
     - Writable entity points (typical)
     - Notes
   * - ``light.``
     - ``state`` (0/1), ``brightness`` (0–255)
     - On/off and brightness for lights.
   * - ``climate.``
     - ``state`` (0 off, 2 heat, 3 cool, 4 auto), ``temperature``
     - Thermostat mode and setpoint (as configured in HA).
   * - ``input_boolean.``
     - ``state`` (0/1)
     - Helper toggles.
   * - ``switch.``
     - ``state`` (0/1)
     - Simple on/off switches.

Reading (scraping) can cover additional entity types and attributes as long as they appear in your registry; **writes** are
limited to the combinations above unless you extend the driver (see below).

How to control from your own agent
----------------------------------

**Recommended (production-style):** use the **Actuator** agent to create a schedule for your device, then issue
``set_point`` through the Actuator during the scheduled window. This avoids conflicting writes and matches the general
Platform Driver pattern described in :ref:`Driver_Communication`.

**Direct RPC (testing / lab):** another agent (or a small one-shot script) can call the Platform Driver over VIP:

* ``get_point(<device path>, <volttron point name>)``
* ``set_point(<device path>, <volttron point name>, <value>)``

Here ``<device path>`` is the same path used in the config store **without** the ``devices/`` prefix — for example if you
stored the device at ``devices/BUILDING/ZONE/my_ha_device``, the RPC path is ``BUILDING/ZONE/my_ha_device``.

If authentication is enabled on the platform, ad-hoc scripts must either use an authorized identity or you must run a
development instance with ``allow-auth = False`` in ``VOLTTRON_HOME/config`` under ``[volttron]`` (ZMQ only). See
:ref:`non-auth-mode`.

Verifying without VOLTTRON (optional)
-------------------------------------

To validate Home Assistant credentials and entity behavior independently of VOLTTRON, you can call the `Home Assistant REST API
<https://developers.home-assistant.io/docs/api/rest>`_ directly (for example with a small Python script using
``urllib`` or ``requests``). This does not replace the driver; it only helps isolate network or token issues.

How to extend write support to more devices
-------------------------------------------

Adding a new **domain** (for example ``fan.``, ``lock.``) or a new **service** usually requires a **code change** in the
Home Assistant interface implementation:

* File: ``services/core/PlatformDriverAgent/platform_driver/interfaces/home_assistant.py``
* Extend routing in ``_set_point`` (and any helpers) to map registry points to the correct Home Assistant
  ``/api/services/<domain>/<service>`` calls.
* Add or update unit tests under ``services/core/PlatformDriverAgent/tests/`` (mock HTTP where possible).

Follow the same patterns already used for lights, climate, ``input_boolean``, and ``switch``: keep service calls in one
place, reuse shared helpers for binary on/off when appropriate, and keep error messages explicit when a point is not
writable.

After changing the driver, reinstall or reload the Platform Driver as needed, update this documentation if behavior
changes, and run the test suite for the Home Assistant driver.

See also
--------

* :ref:`HomeAssistant-Driver` — full driver documentation and registry examples
* :ref:`Platform-Driver-Configuration` — config store and device topics
* :ref:`non-auth-mode` — disabling VIP authentication for local development (use with care)
