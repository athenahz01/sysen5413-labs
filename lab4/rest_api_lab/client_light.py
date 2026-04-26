"""
SYSEN 5413 - Lab 4 Part 1.3: REST Client (Light-Controlled LED)
Athena Huo

Runs on the UniHiker. Once per second:
  1. Reads the onboard light sensor.
  2. POSTs the value to the laptop server's /light endpoint.
  3. Parses the server's decision ('on' or 'off').
  4. Drives the onboard LED on pin P25 accordingly.
  5. Updates the on-screen GUI with both the reading and the LED state.

This is the closed-loop side of REST-based control:
  sense -> transmit -> [server decides] -> respond -> actuate.
"""

import argparse
import time
import requests

# Unihiker libraries
from unihiker import GUI
from pinpong.board import Board, Pin
from pinpong.extension.unihiker import *

# -----------------------------
# Argument parsing
# -----------------------------
parser = argparse.ArgumentParser(description="Light-controlled LED REST client")
parser.add_argument("server_ip", nargs="?", default="127.0.0.1",
                    help="IP of the laptop running server_light.py")
args = parser.parse_args()
BASE_URL = f"http://{args.server_ip}:5000"

# -----------------------------
# Hardware setup
# -----------------------------
Board().begin()                # Required so I2C/SPI buses are ready
led = Pin(Pin.P25, Pin.OUT)    # Onboard LED on pin P25

# -----------------------------
# GUI setup
# -----------------------------
gui = GUI()
gui.draw_text(text='Light-Controlled LED',
              x=120, y=25, font_size=14,
              origin='center', color='#003366')
gui.draw_text(text=f'Server: {args.server_ip}',
              x=120, y=55, font_size=10,
              origin='center', color='#999999')

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
# Main loop
# -----------------------------
print(f"Client started. Server: {BASE_URL}")
print("Reading light every 1 second. Press Ctrl+C to stop.")

while True:
    # 1. Read the sensor
    light_val = light.read()

    # 2. POST to /light - graceful failure if server is unreachable
    try:
        response = requests.post(
            f"{BASE_URL}/light",
            json={'light': light_val},
            timeout=5,
        )
        response.raise_for_status()
        decision = response.json().get('led', 'off')
        status_label.config(text='Connected', color='#009933')
    except requests.RequestException as e:
        # Don't crash on transient network errors - keep the loop alive.
        print(f"Warning: request failed - {e}")
        status_label.config(text='Server unreachable', color='#CC0000')
        decision = 'off'   # Fail-safe: LED off when we can't reach server

    # 3. Drive the LED based on the server's decision
    led.write_digital(1 if decision == 'on' else 0)

    # 4. Update the on-screen labels
    light_label.config(text=f'Light: {light_val}')
    led_label.config(text=f'LED: {decision.upper()}',
                     color='#009933' if decision == 'on' else '#444444')

    # 5. Print to terminal (for the demo video to make decisions visible)
    print(f"light={light_val:>4}  -> LED {decision}")

    time.sleep(1)