"""
udp_receiver.py

Educational example script for a laptop (or any regular computer).

This script listens for UDP messages sent from a UNIHIKER M10 board.
Whenever it receives a message, it prints the contents to the terminal
and then sends an ACK (acknowledgement) UDP message back to the sender.

The UNIHIKER runs a companion script that:
  - sends UDP messages when on-screen buttons are pressed, and
  - listens for these ACK messages to confirm round-trip communication.

You can run this script on Linux, macOS, or Windows as long as Python 3
is installed. It only uses the Python standard library.
"""

import argparse  # Import argparse so we can parse command-line options like --port.
import socket  # Import socket so we can create and use UDP sockets.


# -----------------------------
# Default configuration values
# -----------------------------

# LISTEN_HOST "0.0.0.0" means "listen on all available network interfaces".
# This lets the script accept UDP packets from any reachable IP address.
LISTEN_HOST = "0.0.0.0"

# LISTEN_PORT is the UDP port number the script will bind to by default.
# This value must match the LAPTOP_PORT used in the UNIHIKER script.
DEFAULT_LISTEN_PORT = 5005


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for this script.

    Currently we support a single optional argument:
      --port PORT   (UDP port to listen on; defaults to DEFAULT_LISTEN_PORT)
    """
    # Create an ArgumentParser object with a short description of the script.
    parser = argparse.ArgumentParser(
        description=(
            "UDP receiver for UNIHIKER M10 demo. "
            "Prints incoming messages and sends ACKs back to the sender."
        )
    )

    # Add an optional --port argument so the user can override the default port.
    parser.add_argument(
        "--port",  # Name of the command-line flag.
        type=int,  # Convert the argument value to an integer.
        default=DEFAULT_LISTEN_PORT,  # Use DEFAULT_LISTEN_PORT if the user does not specify a value.
        help=f"UDP port to listen on (default: {DEFAULT_LISTEN_PORT})",  # Help message shown in --help.
    )

    # Parse the arguments from sys.argv and return the resulting Namespace object.
    return parser.parse_args()


def create_udp_socket(listen_host: str, listen_port: int) -> socket.socket:
    """
    Create and bind a UDP socket for listening to incoming messages.

    :param listen_host: Host/address to bind to (e.g. '0.0.0.0' for all interfaces).
    :param listen_port: UDP port number to listen on.
    :return: A bound UDP socket ready to receive data.
    """
    # Create a new socket using IPv4 (AF_INET) and datagram mode (SOCK_DGRAM).
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Allow this port to be reused quickly after the program exits.
    # This helps when restarting the script frequently.
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to the requested host and port so it can receive data.
    sock.bind((listen_host, listen_port))

    # Return the configured and bound socket to the caller.
    return sock


def receive_loop(sock: socket.socket) -> None:
    """
    Run an infinite loop that receives UDP messages and sends ACKs.

    :param sock: The UDP socket on which to receive and send data.
    """
    # Print a message to let the user know that the script is ready.
    local_host, local_port = sock.getsockname()  # Get the actual bound address and port.
    print(f"Listening for UDP on {local_host}:{local_port} (Ctrl+C to stop)")

    try:
        # Start an infinite loop so we can handle any number of messages.
        while True:
            # Wait (block) until a UDP packet arrives on this socket.
            # 'data' contains the received bytes, and 'addr' contains a tuple
            # (sender_ip, sender_port).
            data, addr = sock.recvfrom(4096)

            try:
                # Try to decode the bytes as UTF-8 text for printing.
                message = data.decode("utf-8")
            except UnicodeDecodeError:
                # If decoding fails, fall back to a representation of the raw bytes.
                message = f"<non-UTF-8 data: {data!r}>"

            # Print a line showing where the message came from and what it contained.
            print(f"From {addr[0]}:{addr[1]} -> {message}")

            # Build an ACK message. Including the original message text can make
            # debugging easier and shows that the laptop saw the full payload.
            ack_text = f"ACK: {message}"

            # Encode the ACK string as UTF-8 bytes before sending.
            ack_bytes = ack_text.encode("utf-8")

            # Send the ACK back to the original sender using the source address.
            # Because UDP is connectionless, we must supply the destination
            # address (IP and port) with every sendto() call.
            sock.sendto(ack_bytes, addr)
    except KeyboardInterrupt:
        # If the user presses Ctrl+C in the terminal, we catch the KeyboardInterrupt
        # so we can exit the loop gracefully instead of showing a long traceback.
        print("\nStopping UDP receiver...")
    finally:
        # In all cases (normal exit or error), close the socket to free the port.
        sock.close()


def main() -> None:
    """
    Main entry point for the script.

    This function ties together argument parsing, socket creation,
    and the main receive/send loop.
    """
    # Parse command-line arguments (for now, just the --port option).
    args = parse_args()

    # Create and bind a UDP socket using the chosen port.
    udp_sock = create_udp_socket(LISTEN_HOST, args.port)

    # Enter the main receive loop, which runs until the user stops the script.
    receive_loop(udp_sock)


# Only run main() if this file is executed as a script.
# This allows the functions above to be imported and reused in other code
# without starting the receiver loop automatically.
if __name__ == "__main__":
    main()