"""
tcp_button_sender_tls.py

TLS-wrapped version of tcp_button_sender.py for the UNIHIKER M10.

Same behavior as the plain TCP sender: two buttons send different messages
to the laptop, which sends ACKs back. All traffic is encrypted with TLS,
so a packet sniffer cannot read the message contents.

Requires: Python ssl module (standard library). You must create a self-signed
certificate on the laptop and copy server.crt to the UNIHIKER. See the
project README for certificate generation and configuration instructions.
"""

import os
import socket
import ssl
import time

from unihiker import GUI


# -----------------------------
# Configuration constants
# -----------------------------

# Set the IP address of the laptop that runs the TLS receiver.
# You MUST change this to match the actual IP of your laptop on the same network.
LAPTOP_IP = "10.3.61.26"

# TLS uses port 5006 by default (plain TCP uses 5005) so both demos can coexist.
LAPTOP_PORT = 5006

# Path to the server's certificate file. The client uses this to verify the
# server's identity. For a self-signed cert, this is the server.crt you
# generated. Adjust this path if your certs are stored elsewhere.
# Example: "/home/pi/tcp_udp_test/certs/server.crt"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_FILE = os.path.join(SCRIPT_DIR, "certs", "server.crt")

NODE_NAME = "UNIHIKER_M10"


# -----------------------------
# TLS socket setup
# -----------------------------

tcp_socket = None
connected = False
last_send_time = None


def ensure_connected() -> bool:
    """
    Ensure we have an active TLS connection to the laptop.
    Creates a TCP socket, connects, wraps it with TLS, and performs the handshake.
    Returns True if connected, False otherwise.
    """
    global tcp_socket, connected
    if connected and tcp_socket is not None:
        return True
    if tcp_socket is not None:
        try:
            tcp_socket.close()
        except OSError:
            pass
        tcp_socket = None
    try:
        # Create SSL context for client.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cafile=CERT_FILE)

        # Create TCP socket and connect.
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        raw_sock.connect((LAPTOP_IP, LAPTOP_PORT))

        # Wrap with TLS. server_hostname is required for hostname verification.
        tcp_socket = context.wrap_socket(raw_sock, server_hostname=LAPTOP_IP)
        connected = True
        return True
    except OSError:
        return False
    except ssl.SSLError:
        return False


# -----------------------------
# GUI setup
# -----------------------------

gui = GUI()
MAX_CHARS_PER_LINE = 18

status_line1 = gui.draw_text(
    text="Waiting for button press...",
    x=120,
    y=18,
    font_size=10,
    origin="center",
    color="#0000FF",
)
status_line2 = gui.draw_text(
    text="",
    x=120,
    y=34,
    font_size=10,
    origin="center",
    color="#0000FF",
)
status_line3 = gui.draw_text(
    text="",
    x=120,
    y=50,
    font_size=10,
    origin="center",
    color="#0000FF",
)


# -----------------------------
# Helper function to update status text
# -----------------------------

def update_status(message: str) -> None:
    """Update the on-screen status text, splitting long messages across up to 3 lines."""
    lines = []
    remaining = message.strip()
    while remaining and len(lines) < 3:
        if len(remaining) <= MAX_CHARS_PER_LINE:
            lines.append(remaining)
            remaining = ""
        else:
            break_at = remaining.rfind(" ", 0, MAX_CHARS_PER_LINE + 1)
            if break_at <= 0:
                break_at = MAX_CHARS_PER_LINE
            lines.append(remaining[:break_at].strip())
            remaining = remaining[break_at:].strip()
    status_line1.config(text=lines[0] if len(lines) > 0 else "")
    status_line2.config(text=lines[1] if len(lines) > 1 else "")
    status_line3.config(text=lines[2] if len(lines) > 2 else "")


# -----------------------------
# Button callback functions
# -----------------------------

def on_button1_click() -> None:
    """Callback for the first button."""
    global connected, tcp_socket, last_send_time
    message = f"{NODE_NAME}: BUTTON_1_PRESSED"
    update_status("Sending message from Button 1...")

    if not ensure_connected():
        update_status("Not connected. Start laptop receiver first.")
        return

    try:
        tcp_socket.sendall(message.encode("utf-8"))
        last_send_time = time.time()
        update_status("Button 1 message sent. Waiting for ACK...")
    except OSError as e:
        connected = False
        if tcp_socket is not None:
            try:
                tcp_socket.close()
            except OSError:
                pass
            tcp_socket = None
        update_status(f"Error sending from Button 1: {e}")


def on_button2_click() -> None:
    """Callback for the second button."""
    global connected, tcp_socket, last_send_time
    message = f"{NODE_NAME}: BUTTON_2_PRESSED"
    update_status("Sending message from Button 2...")

    if not ensure_connected():
        update_status("Not connected. Start laptop receiver first.")
        return

    try:
        tcp_socket.sendall(message.encode("utf-8"))
        last_send_time = time.time()
        update_status("Button 2 message sent. Waiting for ACK...")
    except OSError as e:
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

button1 = gui.add_button(
    x=120,
    y=110,
    w=140,
    h=40,
    text="Send Button 1",
    origin="center",
    onclick=on_button1_click,
)
button2 = gui.add_button(
    x=120,
    y=170,
    w=140,
    h=40,
    text="Send Button 2",
    origin="center",
    onclick=on_button2_click,
)


# -----------------------------
# Background ACK listener
# -----------------------------

def listen_for_acks() -> None:
    """Background thread that listens for ACK messages from the laptop."""
    global connected, tcp_socket, last_send_time
    while True:
        try:
            if not connected or tcp_socket is None:
                time.sleep(0.2)
                continue
            data = tcp_socket.recv(4096)
            if not data:
                connected = False
                update_status("Connection closed by laptop.")
                continue

            text = data.decode("utf-8")
            if "BUTTON_1" in text:
                ack_message = f"ACK received: Button 1 From {LAPTOP_IP}"
            elif "BUTTON_2" in text:
                ack_message = f"ACK received: Button 2 From {LAPTOP_IP}"
            else:
                ack_message = f"Received ACK from {LAPTOP_IP} -> {text}"

            if last_send_time is not None:
                rtt_ms = (time.time() - last_send_time) * 1000
                ack_message = f"RTT: {rtt_ms:.0f} ms. " + ack_message

            update_status(ack_message)
        except UnicodeDecodeError:
            update_status("Received ACK (non-UTF-8 data)")
        except OSError as e:
            connected = False
            if tcp_socket is not None:
                try:
                    tcp_socket.close()
                except OSError:
                    pass
                tcp_socket = None
            update_status(f"Socket error in ACK listener: {e}")

        time.sleep(0.1)


ack_thread = gui.start_thread(listen_for_acks)


# -----------------------------
# Main loop
# -----------------------------

def main_loop() -> None:
    """Keep the script running."""
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        global tcp_socket
        if tcp_socket is not None:
            try:
                tcp_socket.close()
            except OSError:
                pass


if __name__ == "__main__":
    main_loop()