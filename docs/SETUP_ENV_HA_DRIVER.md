### Environment Setup for VOLTTRON + Home Assistant Driver

This document describes how to set up the environment required to use the VOLTTRON **Home Assistant (HA) driver**, including installing and running both Home Assistant and VOLTTRON.

---

## 1. Architecture Overview

- **Home Assistant (HA)** runs as a separate service, connected to your physical or virtual devices (lights, thermostats, switches, sensors, etc.).
- **VOLTTRON** runs as a platform and uses the **Home Assistant driver** to connect to HA via HTTP (REST API).
- The driver code in `home_assistant.py` **does not include Home Assistant itself**; it only connects to an already-running HA instance.

To test the HA driver, you must have:

- A running **Home Assistant** instance.
- A running **VOLTTRON** instance with the **Platform Driver Agent** installed.

---

## 2. Host OS and Basic Tools

- **Recommended OS for VOLTTRON**: Linux (e.g. Ubuntu 22.04).
- **Python**: 3.10
- **Git**: to clone the VOLTTRON repository.

If you are on **Windows**, you should run VOLTTRON in one of:

- **WSL2** with Ubuntu, or
- A Linux virtual machine (VirtualBox, VMware, etc.), or
- A Linux container/host in Docker.

All commands below assume you are inside a Linux shell.

---

## 3. Install and Run Home Assistant

You can run Home Assistant in multiple ways. For quick testing, **Docker** is usually simplest.

### 3.1 Option A: Home Assistant via Docker (recommended for testing)

1. Install Docker (on Ubuntu/Debian):

   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io
   sudo systemctl enable --now docker
   ```

2. Run the Home Assistant container:

   ```bash
   sudo docker run -d \
     --name home-assistant \
     --restart=unless-stopped \
     -e TZ=Etc/UTC \
     -p 8123:8123 \
     -v /home/youruser/homeassistant:/config \
     ghcr.io/home-assistant/home-assistant:stable
   ```

   - Replace `/home/youruser/homeassistant` with a real directory path on your host.
   - This exposes Home Assistant on `http://<host-ip>:8123`.

3. Wait 1–2 minutes, then open HA in a browser:

   - On the same machine: `http://localhost:8123`
   - From another machine: `http://<host-ip>:8123`

4. Follow HA’s first-run wizard and create an admin user.

### 3.2 Option B: Existing Home Assistant (Raspberry Pi, NAS, etc.)

If you already have a Home Assistant instance running (for example, Home Assistant OS on a Raspberry Pi), you can reuse it:

- Find its **IP address** and **HTTP port** (usually 8123).
- Ensure your VOLTTRON host can reach `http://<HA-IP>:8123` over the network.

---

## 4. Collect Home Assistant Connection Details

The VOLTTRON HA driver needs three values:

- **IP address** of the HA host
- **Port** (default `8123`)
- **Long-Lived Access Token**

### 4.1 IP and Port

If you can open HA in a browser, the address bar shows something like:

- `http://192.168.1.100:8123` → IP = `192.168.1.100`, port = `8123`
- `http://localhost:8123` → IP = `127.0.0.1` (when VOLTTRON runs on the same machine)

If HA runs on another machine:

- Use `hostname -I` or `ip addr` on that machine to get the IP.
- Check your router’s “connected devices” list if needed.

### 4.2 Create a Long-Lived Access Token

1. Open the HA web UI and log in.
2. Click your **user avatar/name** (usually bottom-left) to open the **Profile** page.
3. Scroll down to **“Long-Lived Access Tokens”**.
4. Click **“Create Token”**, enter a name (e.g. `volttron`), and confirm.
5. **Copy and save** the generated token string in a secure place (it is only shown once).

You will use this token as the `access_token` field in the VOLTTRON driver configuration.

---

## 5. Install VOLTTRON and Dependencies

### 5.1 System Packages (Ubuntu / Debian)

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential libffi-dev python3-dev python3.10 python3.10-venv \
  openssl libssl-dev libevent-dev git
```

### 5.2 Clone VOLTTRON

```bash
cd /path/to/workspace
git clone https://github.com/VOLTTRON/volttron --branch main
cd volttron
```

### 5.3 Bootstrap and Create Virtual Environment

```bash
python3 bootstrap.py --drivers
source env/bin/activate
```

- `--drivers` installs additional dependencies used by the Platform Driver framework.
- `env/` is the Python virtual environment that VOLTTRON will use.

---

## 6. Start the VOLTTRON Platform

Choose a directory for `VOLTTRON_HOME` (for example, `~/.volttron`):

```bash
export VOLTTRON_HOME=~/.volttron
volttron -vv -l volttron.log &
```

- `-vv` enables verbose logging.
- `-l volttron.log` writes logs to `volttron.log`.
- The `&` runs VOLTTRON in the background.

You can watch the logs with:

```bash
tail -f volttron.log
```

---

## 7. Install Platform Driver and Listener Agents

To use the Home Assistant driver, you need the **Platform Driver Agent** and a simple **Listener Agent** to observe data on the message bus.

### 7.1 Install the Listener Agent

```bash
vctl install examples/ListenerAgent --start
```

The Listener subscribes to topics such as `devices/.../all` and prints them to the platform log.

### 7.2 Install the Platform Driver Agent

```bash
python scripts/install-agent.py \
  -s services/core/PlatformDriverAgent \
  --vip-identity platform.driver \
  --start
```

This installs and starts the Platform Driver Agent, which will later load your Home Assistant driver configuration from the configuration store.

---

## 8. Next Steps: Configure the Home Assistant Driver

After the environment is set up:

1. **Create a registry JSON** that describes your HA entity and its points (for example, a light’s `state` and `brightness`).
2. **Create a device configuration JSON** that includes:
   - `driver_type: "home_assistant"`
   - `driver_config` with `ip_address`, `port`, `access_token`
   - `registry_config: "config://<your-registry-name>.json"`
3. Use `vctl config store` to store both the registry and device configs under the `platform.driver` identity.
4. Use RPC calls to test:
   - **Read**: `get_point` and `scrape_all`
   - **Write**: `set_point` to control the light (on/off, brightness)

For a concrete example of light configuration and read/write testing, see the dedicated document for the Home Assistant light driver (e.g. `SETUP_AND_MOCK_LIGHT.md`).

