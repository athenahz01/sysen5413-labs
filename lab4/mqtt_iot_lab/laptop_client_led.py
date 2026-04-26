"""
SYSEN 5413 - Lab 4 Part 2.3: MQTT Client - Laptop side (decision authority)
Author: Athena Huo
Date: April 2026

Runs on the laptop. The "brain" of the closed-loop system:

  1. Subscribes to "iot/sensors" - receives light readings from the Unihiker.
  2. For each reading, applies the on/off threshold.
  3. Publishes the resulting decision ("on" / "off") to "iot/commands".

The Unihiker, on its side, subscribes to "iot/commands" and drives the LED
accordingly. Note the laptop has NO IDEA which device is publishing or
how many devices are listening - that is the broker's problem. This is the
central decoupling promise of pub/sub.
"""
import json
import os
import ssl
import paho.mqtt.client as mqtt
from dotenv import find_dotenv, load_dotenv

# -----------------------------
# Credentials from .env
# -----------------------------
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

TOPIC_SENSORS  = "iot/sensors"      # we subscribe here
TOPIC_COMMANDS = "iot/commands"     # we publish here

# Threshold for "is it dark?" - same logic as the REST version in Part 1,
# different transport. Indoor: 0 = pitch dark, ~4095 = bright sunlight.
LIGHT_THRESHOLD = 50


# -----------------------------
# MQTT setup
# -----------------------------
mqtt_client = mqtt.Client(client_id="laptop_client_led")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to HiveMQ Cloud.")
        client.subscribe(TOPIC_SENSORS)
        print(f"Subscribed to '{TOPIC_SENSORS}'. Waiting for sensor data...")
    else:
        print(f"Connection failed with rc={rc}")


def on_message(client, userdata, msg):
    """
    Called when the broker delivers a sensor reading.
    Decides on/off and publishes the decision back to iot/commands.
    """
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        light_value = int(data.get('light', 0))
    except (json.JSONDecodeError, TypeError, ValueError):
        print(f"Invalid sensor payload: {msg.payload!r}")
        return

    # Decision logic
    decision = 'on' if light_value < LIGHT_THRESHOLD else 'off'
    print(f"light={light_value:>4}  -> publishing '{decision}'")

    # Publish back to commands topic
    client.publish(TOPIC_COMMANDS, decision)


mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# TLS + auth
mqtt_client.username_pw_set(BROKER_USERNAME, BROKER_PASSWORD)
ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
ssl_ctx.load_default_certs()
mqtt_client.tls_set_context(ssl_ctx)

mqtt_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

# loop_forever() is blocking - all work happens in callbacks.
print(f"Light threshold: {LIGHT_THRESHOLD} (below = LED on)")
print("Press Ctrl+C to stop.")
try:
    mqtt_client.loop_forever()
except KeyboardInterrupt:
    print("\nDisconnecting...")
    mqtt_client.disconnect()