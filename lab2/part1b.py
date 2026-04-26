"""
SYSEN 5413 - Lab 2 Part 1b: IMU Fall Detector
Athena Huo

Uses the onboard 6-axis IMU (accelerometer + gyroscope) to detect a fall.

Physics: when the device sits still, gravity registers as ~1.0 g of total
acceleration along the Z axis. During free-fall the sensor falls *with*
gravity, so it no longer 'feels' gravity, and the magnitude
sqrt(x^2 + y^2 + z^2) drops toward 0.

Strategy: poll the IMU at 20 Hz (every 50 ms) and trigger an alert
whenever the magnitude drops below FALL_THRESHOLD g.
"""

# --- Imports ---
from unihiker import GUI
from pinpong.board import Board
from pinpong.extension.unihiker import *
import time

# --- Tuning constant ---
# Below this magnitude (in g), we declare a fall.
# Stationary  ~ 1.0  | walking ~ 0.8-1.4  | flick/free-fall < 0.5
FALL_THRESHOLD = 0.4

# How long the alert stays on screen after a fall is detected, in seconds.
# Without this, the alert would clear instantly when the device hits the
# ground and reads ~1g again - too fast for the user to see.
ALERT_HOLD_SECONDS = 1.5

# --- Hardware setup ---
Board().begin()
gui = GUI()

# --- Screen layout ---
gui.draw_text(text='Fall Detector', x=120, y=25,
              font_size=18, origin='center', color='#003366')

# Live X / Y / Z / strength readouts
gui.draw_text(text='X:', x=20, y=70,  font_size=14, color='#444444')
gui.draw_text(text='Y:', x=20, y=100, font_size=14, color='#444444')
gui.draw_text(text='Z:', x=20, y=130, font_size=14, color='#444444')
gui.draw_text(text='|a|:', x=20, y=170, font_size=16, color='#000000')

x_label   = gui.draw_text(text='--', x=70,  y=70,  font_size=14)
y_label   = gui.draw_text(text='--', x=70,  y=100, font_size=14)
z_label   = gui.draw_text(text='--', x=70,  y=130, font_size=14)
mag_label = gui.draw_text(text='--', x=70,  y=170, font_size=16, color='#FF6600')

# Status banner - changes from "Stable" to "FALL DETECTED!"
status_label = gui.draw_text(text='Stable', x=120, y=240,
                             font_size=20, origin='center', color='#009933')

# --- Main polling loop ---
print(f'Fall detector running. Threshold = {FALL_THRESHOLD} g. Ctrl+C to stop.')

# Track when we last detected a fall, so the alert stays visible briefly.
last_fall_time = 0.0

while True:
    # Read all 4 values
    x = accelerometer.get_x()
    y = accelerometer.get_y()
    z = accelerometer.get_z()
    strength = accelerometer.get_strength()

    # Update on-screen readouts (rounded for readability)
    x_label.config(text=f'{x:+.2f}')
    y_label.config(text=f'{y:+.2f}')
    z_label.config(text=f'{z:+.2f}')
    mag_label.config(text=f'{strength:.2f} g')

    # Detection logic
    now = time.time()
    if strength < FALL_THRESHOLD:
        last_fall_time = now
        print(f'FALL DETECTED  strength={strength:.3f}')

    # Decide what banner to show:
    # - if a fall was JUST detected, hold the alert for ALERT_HOLD_SECONDS
    # - otherwise show the calm "Stable"
    if now - last_fall_time < ALERT_HOLD_SECONDS:
        status_label.config(text='!! FALL DETECTED !!', color='#CC0000')
    else:
        status_label.config(text='Stable', color='#009933')

    # 50 ms = 20 Hz polling. Fast enough to catch a real fall.
    time.sleep(0.05)