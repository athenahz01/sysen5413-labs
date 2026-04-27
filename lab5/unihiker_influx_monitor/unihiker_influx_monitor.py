import os
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(usecwd=True))
import time
from datetime import datetime

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from pinpong.board import *
from pinpong.extension.unihiker import *
from unihiker import GUI

from graph_gui import GraphGUI


# -----------------------------
# Configuration
# -----------------------------

# TODO: Add your own InfluxDB credentials here
INFLUX_URL = os.environ.get("INFLUX_URL", "**************")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "**************")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "MyUnihiker")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "light_data_bucket")

N_POINTS = int(os.environ.get("N_POINTS", "30"))
SENSOR_INTERVAL = float(os.environ.get("SENSOR_INTERVAL", "3"))
PLOT_INTERVAL = float(os.environ.get("PLOT_INTERVAL", "10"))


# -----------------------------
# InfluxDB client setup
# -----------------------------

def create_influx_client():
    if not INFLUX_URL or not INFLUX_TOKEN or not INFLUX_ORG or not INFLUX_BUCKET:
        # We still create a client; writes/queries will fail and be surfaced in the status text.
        pass
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=5000)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    query_api = client.query_api()
    return client, write_api, query_api


influx_client, write_api, query_api = create_influx_client()


def write_light_to_influx(light_value, graph):
    """Write a single light sensor reading to InfluxDB."""
    try:
        point = (
            Point("unihiker_light")
            .tag("device", "unihiker_m10")
            .field("value", int(light_value))
            .time(datetime.utcnow(), WritePrecision.S)
        )
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        graph.set_status(f"Last write OK, light={light_value}")
    except Exception as exc:
        graph.set_status(f"Write error: {exc}")


def query_last_n_points(n_points, graph):
    """Query the last N light readings from InfluxDB."""
    if not INFLUX_BUCKET:
        graph.set_status("No bucket configured; cannot query")
        return []

    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "unihiker_light" and r._field == "value" and r.device == "unihiker_m10")
  |> sort(columns: ["_time"], desc: false)
  |> tail(n: {n_points})
'''
    try:
        tables = query_api.query(flux)
        points = []
        for table in tables:
            for record in table.records:
                points.append((record.get_time(), record.get_value()))
        graph.set_status(f"Last query OK, got {len(points)} points")
        return points
    except Exception as exc:
        graph.set_status(f"Query error: {exc}")
        return []


# -----------------------------
# UniHiker GUI setup
# -----------------------------

gui = GUI()
graph = GraphGUI(gui, n_points=N_POINTS)


# -----------------------------
# Plot thread function
# -----------------------------

def plot_loop(graph):
    while True:
        try:
            points = query_last_n_points(N_POINTS, graph)
            graph.redraw_scatter(points)
        except Exception as exc:
            graph.set_status(f"Plot error: {exc}")
        time.sleep(PLOT_INTERVAL)


# -----------------------------
# Sensor setup and main loop
# -----------------------------

Board().begin()


def main_loop(graph):
    while True:
        try:
            light_value = light.read()
            graph.set_value(f"Light: {light_value}")
            write_light_to_influx(light_value, graph)
        except Exception as exc:
            graph.set_status(f"Sensor error: {exc}")
        time.sleep(SENSOR_INTERVAL)


if __name__ == "__main__":
    gui.start_thread(lambda: plot_loop(graph))
    main_loop(graph)