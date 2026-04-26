"""
unihiker_client.py - MQTT client for UniHiker M10.
Publishes light level to iot/sensors every 3 seconds.
Subscribes to iot/commands and displays received messages on screen.
Runs on UniHiker M10 with HiveMQ Cloud as broker.
"""

import json
import ssl
import time

import paho.mqtt.client as mqtt
from unihiker import GUI
from pinpong.board import *
from pinpong.extension.unihiker import *


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
TOPIC_PUBLISH = "iot/sensors"
TOPIC_SUBSCRIBE = "iot/commands"


# -----------------------------
# GUI setup - one label updated in-place when commands arrive
# -----------------------------

gui = GUI()
command_label = gui.draw_text(
    text="Waiting for commands...",
    x=120,
    y=100,
    font_size=12,
    origin="center",
    color="#0000FF",
)

# -----------------------------
# Light sensor setup (PinPong extension on UniHiker)
# -----------------------------

Board().begin()

# -----------------------------
# MQTT client setup
# -----------------------------

mqtt_client = mqtt.Client(client_id="unihiker_m10")


def on_connect(client, userdata, flags, rc):
    """Called when connected to the broker. Subscribe to commands topic."""
    client.subscribe(TOPIC_SUBSCRIBE)


def on_message(client, userdata, msg):
    """Called when a message arrives. Update screen and print to stdout."""
    payload = msg.payload.decode("utf-8")
    command_label.config(text=payload)
    print(f"Received command: {payload}")


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
# Main loop - publish light level every 3 seconds
# -----------------------------

while True:
    light_value = light.read()
    payload = {
        "light": light_value,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    }
    payload_str = json.dumps(payload)
    mqtt_client.publish(TOPIC_PUBLISH, payload_str)
    print(f"Published: {payload_str}")
    time.sleep(3)