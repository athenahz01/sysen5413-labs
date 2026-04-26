"""
SYSEN 5413 - Lab 2 Part 2a: Polling-Based Button → LED
Athena Huo

Demonstrates the POLLING approach to handling a button press:
the main loop continuously checks the state of Button A and reacts
accordingly. The LED on pin P25 mirrors the button's state.

Trade-off (compare with part2b.py):
  - Polling is simple and predictable.
  - But the CPU is constantly checking, even when nothing has happened,
    and response time is bounded below by the loop period (50 ms here).
"""

# --- Imports ---
from unihiker import GUI
from pinpong.board import Board, Pin             # Pin lets us drive the LED
from pinpong.extension.unihiker import *         # Gives us 'button_a'
import time

# --- Hardware setup ---
Board().begin()
gui = GUI()

# Configure pin P25 (the onboard LED) as a digital output
led = Pin(Pin.P25, Pin.OUT)

# --- Screen layout ---
gui.draw_text(text='Polling Demo', x=120, y=30,
              font_size=18, origin='center', color='#003366')

gui.draw_text(text='Hold Button A', x=120, y=80,
              font_size=14, origin='center', color='#666666')

# Status text - we update this with .config() based on button state
status_label = gui.draw_text(text='Waiting...', x=120, y=160,
                             font_size=22, origin='center', color='#999999')

# Visual LED indicator on screen (so the demo is visible even
# without flipping the board over to see the real LED on P25)
led_indicator = gui.draw_text(text='LED OFF', x=120, y=230,
                              font_size=16, origin='center', color='#444444')

# --- Main polling loop ---
print('Polling button A. Press Ctrl+C to stop.')

while True:
    # ASK the hardware: is Button A pressed RIGHT NOW?
    if button_a.is_pressed():
        led.write_digital(1)                                  # LED on
        status_label.config(text='Pressed', color='#009933')  # green
        led_indicator.config(text='LED ON', color='#009933')
    else:
        led.write_digital(0)                                  # LED off
        status_label.config(text='Waiting...', color='#999999')
        led_indicator.config(text='LED OFF', color='#444444')

    # The 50 ms is the polling period. Smaller = snappier but more CPU.
    # Larger = laggier but easier on the chip. Lab spec suggests 50 ms.
    time.sleep(0.05)