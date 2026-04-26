"""
tcp_button_sender.py

Educational example script for the UNIHIKER M10 single-board computer.

This script creates two on-screen buttons on the UNIHIKER's display.
When you press either button, the UNIHIKER sends a different TCP
message to a laptop on the same network over a persistent TCP connection.

The laptop runs a companion script that listens for TCP connections,
receives these messages, prints them, and sends an ACK (acknowledgement)
back over the same connection.

This script also starts a background listener thread that waits for
ACK messages from the laptop. When an ACK is received, the script
updates the on-screen text so you can see that the round-trip
communication was successful.
"""

import socket  # Import the socket module so we can create and use TCP sockets.
import time  # Import the time module for adding small delays in the ACK listener loop.

from unihiker import GUI  # Import the GUI class from the UNIHIKER library to draw widgets and buttons.

from pinpong.board import Board
from pinpong.extension.unihiker import *
Board().begin()

# -----------------------------
# Configuration constants
# -----------------------------

# Set the IP address of the laptop that will run the TCP receiver script.
# You MUST change this to match the actual IP of your laptop on the same network.
LAPTOP_IP = "10.3.61.26"  # Example IP address; replace with your laptop's IP address.

# Set the TCP port number on which the laptop's receiver script is listening.
# This value must match the LISTEN_PORT used in the laptop script.
LAPTOP_PORT = 5005  # A commonly used example TCP port for testing.

# Optionally, you can change this string to identify this UNIHIKER on the network.
NODE_NAME = "UNIHIKER_M10"  # Used inside messages to show which device sent them.


# -----------------------------
# TCP socket setup
# -----------------------------

# Create a TCP socket using IPv4 (AF_INET) and stream mode (SOCK_STREAM).
# We will (re)create this socket in ensure_connected() when needed.
tcp_socket = None

# Track whether we are connected to the laptop. Used by button callbacks and ACK listener.
connected = False

# Time of last send (for round-trip time). Set by button callbacks, read by ACK listener.
last_send_time = None


def ensure_connected() -> bool:
    """
    Ensure we have an active TCP connection to the laptop.
    If not connected, create a socket (if needed) and attempt to connect.
    Returns True if connected, False otherwise.
    """
    global tcp_socket, connected
    if connected and tcp_socket is not None:
        return True
    # If the socket exists but we're not connected, it may be closed or broken; replace it.
    if tcp_socket is not None:
        try:
            tcp_socket.close()
        except OSError:
            pass
        tcp_socket = None
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_socket.connect((LAPTOP_IP, LAPTOP_PORT))
        connected = True
        return True
    except OSError:
        return False


# -----------------------------
# GUI setup
# -----------------------------

# Create a GUI object, which represents the UNIHIKER screen and lets us draw widgets.
gui = GUI()

# Draw three lines of text near the top of the screen for status messages.
# Use a small font (10px) so text fits on the 240×320 pixel display.
# Long messages (e.g. ACK text) are split across up to three lines.
MAX_CHARS_PER_LINE = 18  # Characters per line at 10px font on 240px width (3 lines).

status_line1 = gui.draw_text(
    text="Waiting for button press...",  # First line of status.
    x=120,  # X coordinate (centered on 240px-wide screen).
    y=18,  # Y coordinate for the first line.
    font_size=10,  # Small font for 240×320 screen.
    origin="center",  # Center the text at (x, y).
    color="#0000FF",  # Blue for visibility.
)

status_line2 = gui.draw_text(
    text="",  # Second line; used when message wraps to multiple lines.
    x=120,  # Same x as line 1 so all lines are centered.
    y=34,  # Y coordinate just below line 1 (about 16px apart for 10px font).
    font_size=10,  # Same size as line 1.
    origin="center",  # Center the text at (x, y).
    color="#0000FF",  # Same blue as line 1.
)

status_line3 = gui.draw_text(
    text="",  # Third line; used for the longest messages (e.g. full ACK text).
    x=120,  # Same x as line 1 and 2.
    y=50,  # Y coordinate just below line 2.
    font_size=10,  # Same size as line 1 and 2.
    origin="center",  # Center the text at (x, y).
    color="#0000FF",  # Same blue as line 1 and 2.
)


# -----------------------------
# Helper function to update status text
# -----------------------------

def update_status(message: str) -> None:
    """
    Convenience function that updates the on-screen status text.

    Long messages are split across up to three lines so they fit on the
    240×320 display. Splits happen at the last space before MAX_CHARS_PER_LINE
    to avoid breaking words.
    """
    lines = []  # Will hold at most 3 strings, each fitting in one line.
    remaining = message.strip()
    while remaining and len(lines) < 3:
        if len(remaining) <= MAX_CHARS_PER_LINE:
            # Rest of message fits on one line.
            lines.append(remaining)
            remaining = ""
        else:
            # Find a break point at the last space before the limit.
            break_at = remaining.rfind(" ", 0, MAX_CHARS_PER_LINE + 1)
            if break_at <= 0:
                break_at = MAX_CHARS_PER_LINE
            lines.append(remaining[:break_at].strip())
            remaining = remaining[break_at:].strip()
    # Update the three status widgets; use "" for any unused lines.
    status_line1.config(text=lines[0] if len(lines) > 0 else "")
    status_line2.config(text=lines[1] if len(lines) > 1 else "")
    status_line3.config(text=lines[2] if len(lines) > 2 else "")


# -----------------------------
# Button callback functions
# -----------------------------

def on_button1_click() -> None:
    """
    Callback for the first button.

    This function is called automatically by the GUI library whenever
    the user taps or clicks the first button on the UNIHIKER screen.
    """
    global connected, tcp_socket, last_send_time
    # Build a message string that clearly identifies:
    # - which UNIHIKER node sent the message
    # - which virtual button was pressed
    message = f"{NODE_NAME}: BUTTON_1_PRESSED"

    # Update the on-screen text so the user knows a message is being sent.
    update_status("Sending message from Button 1...")

    if not ensure_connected():
        update_status("Not connected. Start laptop receiver first.")
        return

    try:
        # Encode the message string as UTF-8 bytes and send it via TCP
        # to the laptop on the existing connection.
        tcp_socket.sendall(message.encode("utf-8"))

        # Record send time for round-trip measurement.
        last_send_time = time.time()

        # If sendall() succeeds, tell the user we are now waiting for an ACK.
        update_status("Button 1 message sent. Waiting for ACK...")
    except OSError as e:
        # If something goes wrong with the network (e.g. connection reset),
        # show the error on the screen and mark as disconnected.
        connected = False
        if tcp_socket is not None:
            try:
                tcp_socket.close()
            except OSError:
                pass
            tcp_socket = None
        update_status(f"Error sending from Button 1: {e}")


def on_button2_click() -> None:
    """
    Callback for the second button.

    This function is called automatically by the GUI library whenever
    the user taps or clicks the second button on the UNIHIKER screen.
    """
    global connected, tcp_socket, last_send_time
    # Build a slightly different message string so the laptop can
    # distinguish Button 2 presses from Button 1 presses.
    lux = light.read()
    message = f"{NODE_NAME}: LIGHT_SENSOR lux={lux}"
    
    # Update the on-screen text so the user knows a message is being sent.
    update_status("Sending message from Button 2...")

    if not ensure_connected():
        update_status("Not connected. Start laptop receiver first.")
        return

    try:
        # Send the UTF-8 encoded message to the laptop using the same TCP socket.
        tcp_socket.sendall(message.encode("utf-8"))

        # Record send time for round-trip measurement.
        last_send_time = time.time()

        # Inform the user that the message was sent and we are waiting for an ACK.
        update_status("Button 2 message sent. Waiting for ACK...")
    except OSError as e:
        # Display any network-related error and mark as disconnected.
        connected = False
        if tcp_socket is not None:
            try:
                tcp_socket.close()
            except OSError:
                pass
            tcp_socket = None
        update_status(f"Error sending from Button 2: {e}")


# -----------------------------
# Create on-screen buttons
# -----------------------------

# Add the first button to the screen.
button1 = gui.add_button(
    x=120,  # Horizontal position of the button (centered).
    y=110,  # Vertical position of the button (near the upper-middle of the screen).
    w=140,  # Width of the button in pixels.
    h=40,  # Height of the button in pixels.
    text="Send Button 1",  # Label displayed on the button.
    origin="center",  # Use the button's center as the reference point.
    onclick=on_button1_click,  # Function to call when the button is pressed.
)

# Add the second button to the screen, slightly lower than the first.
button2 = gui.add_button(
    x=120,  # Same horizontal position as Button 1 so they line up nicely.
    y=170,  # Place this button below the first one.
    w=140,  # Same width as Button 1 for a consistent look.
    h=40,  # Same height as Button 1.
    text="Send Button 2",  # Label displayed on the second button.
    origin="center",  # Use the button's center as the reference point.
    onclick=on_button2_click,  # Function to call when the button is pressed.
)


# -----------------------------
# Background ACK listener
# -----------------------------

def listen_for_acks() -> None:
    """
    Background function that listens for ACK messages from the laptop.

    This function is intended to run in a separate thread started by
    gui.start_thread(). It waits for incoming data on the same TCP
    connection we use for sending. Whenever an ACK arrives, it updates
    the on-screen status text so the user can see that the message made
    the round trip from UNIHIKER to laptop and back again.
    """
    global connected, tcp_socket, last_send_time
    while True:
        try:
            if not connected or tcp_socket is None:
                time.sleep(0.2)
                continue
            # Wait (block) until data arrives on this TCP connection.
            data = tcp_socket.recv(4096)
            if not data:
                # Connection closed by the other side.
                connected = False
                update_status("Connection closed by laptop.")
                continue

            # Try to decode the incoming bytes as a UTF-8 string.
            text = data.decode("utf-8")

            # Determine which button the ACK is for by checking the payload
            # (laptop echoes our message, e.g. "ACK: UNIHIKER_M10: BUTTON_1_PRESSED").
            if "BUTTON_1" in text:
                ack_message = f"ACK received: Button 1 From {LAPTOP_IP}"
            elif "BUTTON_2" in text:
                ack_message = f"ACK received: Button 2 From {LAPTOP_IP}"
            else:
                # Unknown or unexpected format; show the raw ACK text.
                ack_message = f"Received ACK from {LAPTOP_IP} -> {text}"

            if last_send_time is not None:
                rtt_ms = (time.time() - last_send_time) * 1000
                ack_message = f"RTT: {rtt_ms:.0f} ms. " + ack_message

            # Update the on-screen status text so the user sees which button was acknowledged.
            update_status(ack_message)
        except UnicodeDecodeError:
            # If we cannot decode the bytes as UTF-8, show a generic error message.
            update_status("Received ACK (non-UTF-8 data)")
        except OSError as e:
            # If there is a socket error (e.g. connection reset, socket closed),
            # show the error and mark as disconnected.
            connected = False
            if tcp_socket is not None:
                try:
                    tcp_socket.close()
                except OSError:
                    pass
                tcp_socket = None
            update_status(f"Socket error in ACK listener: {e}")

        # Sleep briefly at the end of each loop to reduce CPU usage.
        time.sleep(0.1)


# Start the ACK listener in a separate thread managed by the GUI system.
ack_thread = gui.start_thread(listen_for_acks)


# -----------------------------
# Main loop
# -----------------------------

def main_loop() -> None:
    """
    Simple main loop that keeps the script running.

    Many UNIHIKER GUI examples use a small infinite loop with a short
    sleep to keep the program alive. The GUI system manages drawing and
    event handling internally, and our button callbacks and ACK listener
    thread will be called as needed.
    """
    try:
        while True:
            # Sleep for a short time so this loop does not consume CPU.
            time.sleep(0.1)
    except KeyboardInterrupt:
        # If the user stops the program from a terminal (Ctrl+C),
        # we try to close the TCP socket cleanly.
        global tcp_socket
        if tcp_socket is not None:
            try:
                tcp_socket.close()
            except OSError:
                pass


# Only run the main loop if this file is executed as a script
# (and not imported as a module by another file).
if __name__ == "__main__":
    main_loop()