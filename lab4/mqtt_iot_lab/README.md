# MQTT IoT Lab

Two Python scripts for an IoT lab using HiveMQ Cloud as the MQTT broker.

## Setup

1. Create a cluster at [HiveMQ Cloud](https://www.hivemq.com/mqtt-cloud-broker/) (free tier available).
2. Copy your cluster hostname, username, and password from the HiveMQ Cloud console.
3. Edit both scripts and set the configuration variables at the top:
   - `BROKER_HOST` — your cluster hostname (e.g. `xxxxx.s1.eu.hivemq.cloud`)
   - `BROKER_USERNAME` — your cluster username
   - `BROKER_PASSWORD` — your cluster password

## Install

**On laptop:**
```bash
pip install -r requirements.txt
```

**On UniHiker M10:** Install `paho-mqtt` and ensure the `unihiker` library is available (usually preinstalled).

## Usage

1. Start the UniHiker client on the M10 (runs the sensor publisher and command display):
   ```bash
   python unihiker_client.py
   ```

2. Start the laptop client (subscribes to sensors, sends your typed input as commands):
   ```bash
   python laptop_client.py
   ```

3. Type a message in the laptop terminal and press Enter — it appears on the UniHiker screen.

## Topics

- `iot/sensors` — UniHiker publishes `{"noise_db": <value>, "timestamp": "<ISO>"}` every second.
- `iot/commands` — Laptop publishes each line you type; UniHiker displays it on screen.