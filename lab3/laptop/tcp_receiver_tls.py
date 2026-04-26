"""
tcp_receiver_tls.py

TLS-wrapped version of tcp_receiver.py for the laptop.

Same behavior as the plain TCP receiver: listens for connections from the
UNIHIKER, prints incoming messages, and sends ACKs back. All traffic is
encrypted with TLS, so a packet sniffer cannot read the message contents.

Requires: Python ssl module (standard library). You must create a self-signed
certificate and configure the paths. See the project README for certificate
generation and configuration instructions.
"""

import argparse
import os
import socket
import ssl


# -----------------------------
# Default configuration values
# -----------------------------

LISTEN_HOST = "0.0.0.0"
DEFAULT_LISTEN_PORT = 5006

# Default cert paths relative to the script. Run from tcp_udp_test/ or laptop/
# and ensure certs/ exists with server.crt and server.key.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CERT = os.path.join(SCRIPT_DIR, "..", "certs", "server.crt")
DEFAULT_KEY = os.path.join(SCRIPT_DIR, "..", "certs", "server.key")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "TLS TCP receiver for UNIHIKER M10 demo. "
            "Accepts TLS connections, prints incoming messages and sends ACKs back."
        )
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_LISTEN_PORT,
        help=f"TCP port to listen on (default: {DEFAULT_LISTEN_PORT})",
    )
    parser.add_argument(
        "--cert",
        type=str,
        default=DEFAULT_CERT,
        help=f"Path to server certificate file (default: {DEFAULT_CERT})",
    )
    parser.add_argument(
        "--key",
        type=str,
        default=DEFAULT_KEY,
        help=f"Path to server private key file (default: {DEFAULT_KEY})",
    )
    return parser.parse_args()


def create_tls_listen_socket(
    listen_host: str,
    listen_port: int,
    certfile: str,
    keyfile: str,
) -> ssl.SSLSocket:
    """
    Create, bind, and listen on a TLS socket for incoming connections.

    :param listen_host: Host/address to bind to.
    :param listen_port: TCP port number to listen on.
    :param certfile: Path to server certificate (e.g. server.crt).
    :param keyfile: Path to server private key (e.g. server.key).
    :return: A listening TLS socket ready to accept connections.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((listen_host, listen_port))
    sock.listen(1)

    ssl_sock = context.wrap_socket(sock, server_side=True)
    return ssl_sock


def serve_client(client_sock: ssl.SSLSocket, client_addr: tuple) -> None:
    """Receive messages from one client and send ACKs back until the connection closes."""
    addr_str = f"{client_addr[0]}:{client_addr[1]}"
    print(f"Client connected from {addr_str}")

    try:
        while True:
            data = client_sock.recv(4096)
            if not data:
                break

            try:
                message = data.decode("utf-8")
            except UnicodeDecodeError:
                message = f"<non-UTF-8 data: {data!r}>"

            print(f"From {addr_str} -> {message}")

            ack_text = f"ACK: {message}"
            client_sock.sendall(ack_text.encode("utf-8"))
    except OSError as e:
        print(f"Error with client {addr_str}: {e}")
    finally:
        client_sock.close()
        print(f"Client {addr_str} disconnected.")


def accept_loop(listen_sock: ssl.SSLSocket) -> None:
    """Run a loop that accepts TLS connections and serves each client in turn."""
    local_host, local_port = listen_sock.getsockname()
    print(f"Listening for TLS on {local_host}:{local_port} (Ctrl+C to stop)")

    try:
        while True:
            client_sock, client_addr = listen_sock.accept()
            serve_client(client_sock, client_addr)
    except KeyboardInterrupt:
        print("\nStopping TLS receiver...")
    finally:
        listen_sock.close()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    listen_sock = create_tls_listen_socket(
        LISTEN_HOST,
        args.port,
        args.cert,
        args.key,
    )
    accept_loop(listen_sock)


if __name__ == "__main__":
    main()