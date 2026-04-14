# Design Document: Expanding Home Assistant Driver Write Capabilities

## Title
Generic Write-Access Support for Volttron Home Assistant Driver

## Context and Scope
Currently, the Volttron Home Assistant (HA) Driver allows the platform to read data from any HA-connected device. However, its control (write-access) functionality is strictly hardcoded to support only two domains: `light` (state and brightness) and `climate`/thermostats (state and temperature). 

As the Home Assistant ecosystem has grown, users increasingly need to control a wider variety of smart devices (e.g., switches, locks, fans, covers) through Volttron. 

**Scope includes:**
* Refactoring the backend Python logic in `home_assistant.py` to construct dynamic API requests.
* Updating the Registry Configuration parser to map Volttron points for new device types.
* Expanding the integration test suite to validate new and legacy devices.
* Updating the Volttron official documentation.

**Out of scope:**
* Adding read-access functionality (this already works universally).
* Developing new Home Assistant integrations outside of the Volttron environment.
* Implementing device-specific scheduling interfaces within Volttron (control will remain command-based).

## Goals and Non-Goals
**Goals:**
* Enable generic, domain-agnostic write-access from Volttron to any valid Home Assistant entity.
* Ensure backward compatibility so that existing configurations for `light` and `climate` devices continue to function without interruption.
* Ensure the driver correctly formats HTTP POST requests to the Home Assistant REST API dynamically based on the device configuration.

**Non-Goals:**
* We will not hardcode a massive new list of "supported" devices. The goal is a universal pass-through, not an expanded allowlist.
* We are not building a graphical user interface (GUI) for device control.

## Proposed Design
To achieve generic write-access, we will modify the `PlatformDriverAgent`'s Home Assistant interface (`home_assistant.py`).

1. **Dynamic API Routing:** Instead of using `if/elif` blocks to check if a device is a `light` or `climate` entity before executing a command, the driver will extract the `domain` (e.g., `switch`, `lock`) and the `service` (e.g., `turn_on`, `lock`) directly from the incoming Volttron RPC call and registry configuration.

2. **Payload Construction:**
   The driver will map the incoming Volttron point values to a generic JSON payload. For example, a command to turn on a switch will dynamically format into an API call to `http://<HA_IP>:<PORT>/api/services/<domain>/<service>` with the entity ID included in the JSON body.

3. **Registry Configuration Updates:**
   We will validate that the existing CSV/JSON registry configuration schemas can accept arbitrary strings for `Units` and `Type` fields without throwing validation errors, ensuring new device domains can be mapped easily.

## Alternatives Considered
* **The "Allowlist" Approach:** We considered simply adding `elif` statements for common requested devices (e.g., `elif domain == 'switch':`). 
  * *Why it was rejected:* This approach incurs high technical debt. Every time a user wants to add a new device type (e.g., a smart vacuum), developers would need to release a new version of the driver.
* **Creating Separate Drivers per Device Type:** We considered creating a `HomeAssistantSwitchDriver`, `HomeAssistantLockDriver`, etc.
  * *Why it was rejected:* This violates the DRY (Don't Repeat Yourself) principle. The underlying HTTP connection and authentication logic to the Home Assistant REST API is identical across all devices.

## Risks and Tradeoffs
* **Risk - Breaking Legacy Deployments:** Refactoring the core write logic risks breaking deployments for users currently relying on the hardcoded `light` and `climate` logic. 
  * *Mitigation:* We will write strict regression tests for lights and thermostats before merging any code.
* **Risk - Unintended Device Behavior:** A generic pass-through means Volttron might send improperly formatted data types (e.g., sending a string to a device expecting a boolean) if the user configures the registry incorrectly.
  * *Mitigation:* We will implement generic error handling that gracefully catches HTTP 400 (Bad Request) errors from Home Assistant and logs them clearly in the Volttron system log.
* **Tradeoff:** By making the driver generic, we shift some of the burden of correctness to the user. The user must ensure their Registry Configuration file perfectly matches the exact service endpoints expected by Home Assistant, as the driver will no longer "hand-hold" or validate specific device commands.

## Open Questions
1. **Complex Payloads:** While simple commands (e.g., `switch.turn_on`) are straightforward, how will our generic implementation handle highly complex, nested JSON payloads required by certain niche Home Assistant devices?
2. **Testing Environment:** Can we successfully mock all device types in our automated GitHub Actions test suite, or will we rely on a live, local Docker instance of Home Assistant for integration testing?