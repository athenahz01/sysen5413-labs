"""
SYSEN 5413 - Lab 4 Part 2.3: MQTT Client (Light-Controlled LED)
Author: Athena Huo
Date: April 2026

Runs on the UniHiker M10. Forms one half of an MQTT-based closed-loop
control system. Compared to the REST version in Part 1:

  - The Unihiker does NOT know the laptop's IP. It only knows the broker.
  - Same in reverse: the laptop has no idea what device is publishing.
  - Communication is decoupled in space (and partially in time) by the broker.

This script:
  1. Subscribes to "iot/commands" - drives the onboard LED based on incoming
     "on" / "off" messages.
  2. Publishes the light sensor reading to "iot/sensors" every 1 second.
  3. Updates the on-screen GUI with both the live reading and the LED state.
"""
import json
import os
import ssl
import time
import paho.mqtt.client as mqtt
from dotenv import find_dotenv, load_dotenv
from unihiker import GUI
from pinpong.board import Board, Pin
from pinpong.extension.unihiker import *

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

TOPIC_PUBLISH   = "iot/sensors"     # we publish here
TOPIC_SUBSCRIBE = "iot/commands"    # we subscribe here

# -----------------------------
# Hardware setup
# -----------------------------
Board().begin()
led = Pin(Pin.P25, Pin.OUT)         # onboard LED on the back of the board

# -----------------------------
# GUI layout
# -----------------------------
gui = GUI()
gui.draw_text(text='MQTT Light → LED', x=120, y=25,
              font_size=14, origin='center', color='#003366')
gui.draw_text(text='Broker: HiveMQ Cloud', x=120, y=55,
              font_size=10, origin='center', color='#999999')

light_label = gui.draw_text(text='Light: ----',
                            x=120, y=120, font_size=18,
                            origin='center', color='#FF6600')
led_label = gui.draw_text(text='LED: ----',
                          x=120, y=170, font_size=18,
                          origin='center', color='#444444')
status_label = gui.draw_text(text='Connecting...',
                             x=120, y=240, font_size=12,
                             origin='center', color='#999999')

# -----------------------------
# MQTT setup
# -----------------------------
mqtt_client = mqtt.Client(client_id="unihiker_m10_led")


def on_connect(client, userdata, flags, rc):
    """Called when the broker accepts our TLS+auth handshake."""
    if rc == 0:
        print("Connected to HiveMQ Cloud.")
        # Subscribe INSIDE on_connect so reconnects auto-resubscribe.
        client.subscribe(TOPIC_SUBSCRIBE)
        status_label.config(text='Connected', color='#009933')
    else:
        print(f"Connection failed with rc={rc}")
        status_label.config(text=f'Connect failed (rc={rc})', color='#CC0000')


def on_message(client, userdata, msg):
    """Called whenever the broker delivers a message on a subscribed topic."""
    payload = msg.payload.decode('utf-8').strip().lower()
    print(f"Received command: '{payload}'")

    # Drive LED based on the command.
    if payload == 'on':
        led.write_digital(1)
        led_label.config(text='LED: ON', color='#009933')
    elif payload == 'off':
        led.write_digital(0)
        led_label.config(text='LED: OFF', color='#444444')
    else:
        # Unknown payload - safest is to leave LED state unchanged.
        print(f"  (ignoring unknown command)")


mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# TLS + auth (HiveMQ Cloud requires both)
mqtt_client.username_pw_set(BROKER_USERNAME, BROKER_PASSWORD)
ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
ssl_ctx.load_default_certs()
mqtt_client.tls_set_context(ssl_ctx)

mqtt_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
mqtt_client.loop_start()    # network thread runs in the background

# -----------------------------
# Main loop: publish light value every 1 second
# -----------------------------
print(f"Publishing to '{TOPIC_PUBLISH}', subscribed to '{TOPIC_SUBSCRIBE}'.")
print("Press Ctrl+C to stop.")

while True:
    light_value = light.read()
    payload = json.dumps({
        'light': light_value,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime()),
    })
    mqtt_client.publish(TOPIC_PUBLISH, payload)
    light_label.config(text=f'Light: {light_value}')
    print(f"Published: {payload}")
    time.sleep(1)