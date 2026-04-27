# UniHiker InfluxDB Light Sensor Monitor

This project runs on a UniHiker M10 board. It reads the onboard light sensor, writes values to an InfluxDB 2.x Cloud bucket, and periodically queries and plots the last **N** readings as a scatter plot on the UniHiker screen.

## Requirements

- UniHiker M10 with the default `unihiker` and `pinpong` libraries installed
- Network connectivity from the UniHiker to InfluxDB Cloud
- Python 3 on the UniHiker

Python dependencies for this project are listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

> On UniHiker, the `unihiker`, `pinpong`, and `tkinter` libraries are already preinstalled.

## InfluxDB Cloud Configuration

This script targets **InfluxDB 2.x / InfluxDB Cloud** and expects the following environment variables to be set on the UniHiker:

- `INFLUX_URL` – InfluxDB Cloud URL, e.g. `https://us-east-1-1.aws.cloud2.influxdata.com`
- `INFLUX_TOKEN` – API token with read/write permissions to the bucket
- `INFLUX_ORG` – InfluxDB organization name
- `INFLUX_BUCKET` – Target bucket name

Example (bash):

```bash
export INFLUX_URL="https://us-east-1-1.aws.cloud2.influxdata.com"
export INFLUX_TOKEN="your-long-secret-token-here"
export INFLUX_ORG="your-org"
export INFLUX_BUCKET="unihiker-light"
```

## What the Script Does

- Reads the onboard light sensor using `light.read()` every few seconds.
- Writes each reading to InfluxDB Cloud as measurement `unihiker_light` with:
  - field `value` (0–4095 integer)
  - tag `device=unihiker_m10`
- In a parallel GUI thread:
  - Queries the last **N** points from InfluxDB.
  - Maps them into the UniHiker 240×320 screen coordinate space.
  - Draws them as a scatter plot (small filled circles) in a plot area.
  - Updates status text (latest value, errors, last refresh time).

## Running the Monitor

1. Copy this folder (`unihiker_influx_monitor`) onto your UniHiker (for example under `/root`).
2. On the UniHiker, install the Python dependency:

   ```bash
   cd /root/unihiker_influx_monitor
   pip install -r requirements.txt
   ```

3. Set the InfluxDB environment variables on the UniHiker shell:

   ```bash
   export INFLUX_URL="https://your-cloud-url"
   export INFLUX_TOKEN="your-token"
   export INFLUX_ORG="your-org"
   export INFLUX_BUCKET="your-bucket"
   ```

4. Run the script:

   ```bash
   python unihiker_influx_monitor.py
   ```

5. You should see:
   - A title and status line at the top of the screen.
   - A scatter plot in the center of the screen showing the last **N** light readings.
   - A small info line at the bottom showing `N` and last refresh time.

## Troubleshooting

- **Nothing appears in InfluxDB**:
  - Double-check `INFLUX_URL`, `INFLUX_ORG`, `INFLUX_BUCKET`, and `INFLUX_TOKEN`.
  - Ensure the token has write access to the bucket.
  - Make sure the UniHiker has network connectivity to the InfluxDB Cloud endpoint.

- **Scatter plot is empty**:
  - It may take some time for enough readings to accumulate for `N` points.
  - Check the status text; if it shows query errors, verify InfluxDB configuration.

- **Script crashes on start**:
  - Confirm that `influxdb-client` is installed with `pip show influxdb-client`.
  - Verify you are running with Python 3 on the UniHiker.