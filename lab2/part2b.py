"""
SYSEN 5413 - Lab 2 Part 2b: Interrupt-Style Button → LED
Athena Huo

Same observable behavior as part2a (Button A pressed → LED on, released
→ LED off), but architected around the INTERRUPT MODEL: callbacks fire
on edge events, and the main loop is idle.

PLATFORM CONSTRAINT (important for the analysis):
  Button A on the Unihiker M10 is exposed through the Linux GPIO
  sysfs interface (/sys/class/gpio/gpio219/) which on this firmware
  does NOT expose an 'edge' file. That means we cannot use epoll
  to block on a kernel-level interrupt. We also confirmed that
  pinpong's button_a.irq() is non-functional on this firmware.

  So the most honest implementation is a dedicated polling thread
  that watches for state TRANSITIONS and dispatches callbacks. From
  the main thread's perspective, this is indistinguishable from a
  true interrupt: callbacks fire on edges, and the main loop is free.
  This is the standard "edge-detection" pattern used in production
  embedded Linux when hardware-level GPIO interrupts aren't available.

WHY THIS STILL COUNTS AS INTERRUPT-STYLE:
  - The MAIN thread does no work. It's not the one checking the button.
  - Callbacks fire only on EDGE events (transitions), never on steady state.
  - From the application's point of view, control flow is event-driven.
  - The polling is isolated to one tiny background thread, freeing the
    main thread to do anything else (UI updates, network I/O, etc.).
"""

# --- Imports ---
from unihiker import GUI
from pinpong.board import Board, Pin
from pinpong.extension.unihiker import *
import threading
import time

# --- Hardware setup ---
Board().begin()
gui = GUI()
led = Pin(Pin.P25, Pin.OUT)

# --- Screen layout ---
gui.draw_text(text='Interrupt Demo', x=120, y=30,
              font_size=18, origin='center', color='#003366')
gui.draw_text(text='Hold Button A', x=120, y=80,
              font_size=14, origin='center', color='#666666')
status_label = gui.draw_text(text='Waiting...', x=120, y=160,
                             font_size=22, origin='center', color='#999999')
led_indicator = gui.draw_text(text='LED OFF', x=120, y=230,
                              font_size=16, origin='center', color='#444444')

press_count = 0
press_count_label = gui.draw_text(text='Presses: 0', x=120, y=280,
                                  font_size=12, origin='center', color='#666666')


# --- Edge-triggered callbacks (called on TRANSITIONS only) ---
def on_button_a_pressed():
    """Fires the moment Button A goes from up → down (rising edge)."""
    global press_count
    press_count += 1
    led.write_digital(1)
    status_label.config(text='Pressed', color='#009933')
    led_indicator.config(text='LED ON', color='#009933')
    press_count_label.config(text=f'Presses: {press_count}')


def on_button_a_released():
    """Fires the moment Button A goes from down → up (falling edge)."""
    led.write_digital(0)
    status_label.config(text='Waiting...', color='#999999')
    led_indicator.config(text='LED OFF', color='#444444')


# --- Background watcher thread ---
def button_watcher():
    """
    Runs in its own thread. Watches for STATE TRANSITIONS on Button A
    and dispatches the appropriate callback. The main thread is never
    involved.

    Note the key difference from part2a's polling: that one used the
    button state directly (LED on whenever pressed). This one only
    fires on EDGES — the transitions themselves — which is the
    semantic of an interrupt. The two callbacks below correspond to
    what would be IRQ_RISING and IRQ_FALLING on a real microcontroller.
    """
    last_state = button_a.is_pressed()    # capture initial state
    while True:
        current = button_a.is_pressed()
        if current != last_state:
            # An EDGE just occurred. Dispatch.
            if current:
                on_button_a_pressed()    # rising edge
            else:
                on_button_a_released()   # falling edge
            last_state = current
        # 10 ms polling interval inside the watcher (100 Hz)
        # This is fast enough that no human-pace press is missed.
        time.sleep(0.01)


# Start the watcher in a daemon thread (dies with the main process)
watcher_thread = threading.Thread(target=button_watcher, daemon=True)
watcher_thread.start()

print('Interrupt-style button monitor running. Press Ctrl+C to stop.')
print('Main loop is idle — all work happens in the watcher thread.')

# --- Main loop: completely idle ---
# This is the key invariant. The main thread does no button work.
# It just sleeps. All event handling happens in the background thread.
while True:
    time.sleep(1)