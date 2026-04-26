"""
SYSEN 5413 - Lab 2 Part 1a: Light Sensor Brightness Display
Athena Huo

Reads the Unihiker M10's onboard light sensor in a loop and displays
the value on the touchscreen. The sensor returns roughly 0-4095:
- ~0     = covered / very dark
- ~4095  = pointed at a bright light source
"""

# --- Imports ---
from unihiker import GUI                        # Touchscreen drawing
from pinpong.board import Board                 # Board init (required)
from pinpong.extension.unihiker import *        # Gives us 'light' object
import time                                     # For sleep()

# --- Hardware setup ---
Board().begin()        # ALWAYS call this first - sets up I2C bus to sensors
gui = GUI()            # Create the GUI object (our drawing canvas)

# --- Build the screen layout ---
# Title at the top - drawn ONCE, never updated
gui.draw_text(text='Light Sensor', x=120, y=30,
              font_size=18, origin='center', color='#003366')

# Static "Reading:" label - drawn ONCE
gui.draw_text(text='Reading:', x=120, y=120,
              font_size=14, origin='center', color='#666666')

# The actual sensor value - drawn ONCE, then UPDATED each loop with .config()
# We assign it to a variable so we can change its text later.
value_label = gui.draw_text(text='----', x=120, y=160,
                            font_size=32, origin='center', color='#FF6600')

# Brightness category text (changes from "Dim" to "Normal" to "Bright")
status_label = gui.draw_text(text='', x=120, y=220,
                             font_size=14, origin='center', color='#009933')

# --- Helper: turn a raw value into a human-readable category ---
def categorize(raw_value):
    if raw_value < 500:
        return 'Dark'
    elif raw_value < 2000:
        return 'Dim'
    elif raw_value < 3500:
        return 'Normal'
    else:
        return 'Bright'

# --- Main polling loop ---
print('Light sensor monitor running. Ctrl+C to stop.')
while True:
    # 1. Read the sensor (returns int 0-4095)
    lux = light.read()

    # 2. Print to terminal too (helpful for debugging)
    print(f'Light reading: {lux}')

    # 3. Update the on-screen value
    value_label.config(text=str(lux))
    status_label.config(text=categorize(lux))

    # 4. Wait 1 second before reading again (lab spec says "every second")
    time.sleep(1)