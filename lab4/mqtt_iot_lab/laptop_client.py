"""
laptop_client.py - MQTT client for developer laptop.
Subscribes to iot/sensors and prints light readings.
Publishes each line from stdin to iot/commands.
Runs on laptop with HiveMQ Cloud as broker.
"""

import json
import ssl

import paho.mqtt.client as mqtt


# -----------------------------
# Configuration (edit these for your HiveMQ Cloud cluster)
# -----------------------------

import os
from dotenv import load_dotenv

# Find .env by walking up from this script's directory.
# This works whether .env is here, in lab4/, or in the project root.
from dotenv import find_dotenv
load_dotenv(find_dotenv(usecwd=True))

BROKER_HOST = os.getenv('HIVEMQ_HOST')
BROKER_PORT = int(os.getenv('HIVEMQ_PORT', '8883'))
BROKER_USERNAME = os.getenv('HIVEMQ_USER')
BROKER_PASSWORD = os.getenv('HIVEMQ_PASS')

if not all([BROKER_HOST, BROKER_USERNAME, BROKER_PASSWORD]):
    raise SystemExit(
        "ERROR: HiveMQ credentials missing. Make sure .env is in the same "
        "directory as this script with HIVEMQ_HOST, HIVEMQ_USER, HIVEMQ_PASS set."
    )
TOPIC_SENSORS = "iot/sensors"
TOPIC_COMMANDS = "iot/commands"


# -----------------------------
# MQTT client setup
# -----------------------------

mqtt_client = mqtt.Client(client_id="laptop_client")


def on_connect(client, userdata, flags, rc):
    """Called when connected to the broker. Subscribe to sensors topic."""
    client.subscribe(TOPIC_SENSORS)


def on_message(client, userdata, msg):
    """Called when a sensor message arrives. Parse JSON and print light and timestamp."""
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        light_value = data.get("light", "?")
        timestamp = data.get("timestamp", "?")
        print(f"Light: {light_value} at {timestamp}")
    except (json.JSONDecodeError, TypeError):
        print(f"Invalid sensor payload: {msg.payload}")


mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# TLS and authentication
mqtt_client.username_pw_set(BROKER_USERNAME, BROKER_PASSWORD)
ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
ssl_ctx.load_default_certs()
mqtt_client.tls_set_context(ssl_ctx)

# Connect and start non-blocking loop
mqtt_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
mqtt_client.loop_start()

# -----------------------------
# Input loop - read from stdin, publish each line to iot/commands
# -----------------------------

print("Connected. Type a message and press Enter to send to iot/commands.")
print("Sensor data will appear below. Press Ctrl+C to exit.")
print("-" * 40)

try:
    while True:
        line = input()
        mqtt_client.publish(TOPIC_COMMANDS, line.strip())
except KeyboardInterrupt:
    mqtt_client.disconnect()
    mqtt_client.loop_stop()
    print("\nDisconnected. Goodbye.")