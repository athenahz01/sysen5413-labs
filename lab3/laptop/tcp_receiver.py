"""
tcp_receiver.py

Educational example script for a laptop (or any regular computer).

This script listens for TCP connections from a UNIHIKER M10 board.
Whenever it receives a message on an accepted connection, it prints
the contents to the terminal and sends an ACK (acknowledgement) back
over the same connection.

The UNIHIKER runs a companion script that:
  - sends TCP messages when on-screen buttons are pressed, and
  - listens for these ACK messages to confirm round-trip communication.

You can run this script on Linux, macOS, or Windows as long as Python 3
is installed. It only uses the Python standard library.
"""

import argparse  # Import argparse so we can parse command-line options like --port.
import socket  # Import socket so we can create and use TCP sockets.


# -----------------------------
# Default configuration values
# -----------------------------

# LISTEN_HOST "0.0.0.0" means "listen on all available network interfaces".
# This lets the script accept TCP connections from any reachable IP address.
LISTEN_HOST = "0.0.0.0"

# LISTEN_PORT is the TCP port number the script will bind to by default.
# This value must match the LAPTOP_PORT used in the UNIHIKER script.
DEFAULT_LISTEN_PORT = 5005


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for this script.

    Currently we support a single optional argument:
      --port PORT   (TCP port to listen on; defaults to DEFAULT_LISTEN_PORT)
    """
    parser = argparse.ArgumentParser(
        description=(
            "TCP receiver for UNIHIKER M10 demo. "
            "Accepts connections, prints incoming messages and sends ACKs back."
        )
    )

    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_LISTEN_PORT,
        help=f"TCP port to listen on (default: {DEFAULT_LISTEN_PORT})",
    )

    return parser.parse_args()


def create_tcp_listen_socket(listen_host: str, listen_port: int) -> socket.socket:
    """
    Create, bind, and listen on a TCP socket for incoming connections.

    :param listen_host: Host/address to bind to (e.g. '0.0.0.0' for all interfaces).
    :param listen_port: TCP port number to listen on.
    :return: A listening TCP socket ready to accept connections.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((listen_host, listen_port))
    sock.listen(1)  # Allow one pending connection in the backlog.
    return sock


def serve_client(client_sock: socket.socket, client_addr: tuple) -> None:
    """
    Receive messages from one client and send ACKs back until the connection closes.

    :param client_sock: The accepted client socket.
    :param client_addr: (address, port) of the client for logging.
    """
    addr_str = f"{client_addr[0]}:{client_addr[1]}"
    print(f"Client connected from {addr_str}")

    try:
        while True:
            # Wait for data on this TCP connection. recv() returns empty bytes when
            # the client closes the connection.
            data = client_sock.recv(4096)
            if not data:
                break

            try:
                message = data.decode("utf-8")
            except UnicodeDecodeError:
                message = f"<non-UTF-8 data: {data!r}>"

            print(f"From {addr_str} -> {message}")

            # Build and send ACK over the same connection.
            ack_text = f"ACK: {message}"
            client_sock.sendall(ack_text.encode("utf-8"))
    except OSError as e:
        print(f"Error with client {addr_str}: {e}")
    finally:
        client_sock.close()
        print(f"Client {addr_str} disconnected.")


def accept_loop(listen_sock: socket.socket) -> None:
    """
    Run a loop that accepts TCP connections and serves each client in turn.

    :param listen_sock: The listening TCP socket.
    """
    local_host, local_port = listen_sock.getsockname()
    print(f"Listening for TCP on {local_host}:{local_port} (Ctrl+C to stop)")

    try:
        while True:
            # Block until a client connects.
            client_sock, client_addr = listen_sock.accept()
            # Serve this client until it disconnects, then accept the next.
            serve_client(client_sock, client_addr)
    except KeyboardInterrupt:
        print("\nStopping TCP receiver...")
    finally:
        listen_sock.close()


def main() -> None:
    """
    Main entry point: parse args, create listening socket, run accept loop.
    """
    args = parse_args()
    listen_sock = create_tcp_listen_socket(LISTEN_HOST, args.port)
    accept_loop(listen_sock)


if __name__ == "__main__":
    main()