"""
sniff.py

Runs on the UNIHIKER M10 and uses Scapy to sniff TCP traffic between the
UNIHIKER and the laptop (the same pair that use tcp_button_sender.py and
tcp_receiver.py). All TCP payloads on the configured port are printed to
the terminal with direction labels.

Use --port 5005 for plain TCP (tcp_button_sender.py / tcp_receiver.py).
Use --port 5006 for TLS (tcp_button_sender_tls.py / tcp_receiver_tls.py).
With TLS, payloads are encrypted and will appear as gibberish.

Requires: pip install scapy
Sniffing raw packets usually requires root: sudo python3 sniff.py
"""

import argparse
import sys

# Optional: allow running without scapy installed for a clear error.
try:
    from scapy.all import sniff, IP, TCP, Raw
    from scapy.error import Scapy_Exception
except ImportError:
    print("Scapy is required. Install with: pip install scapy", file=sys.stderr)
    sys.exit(1)


# -----------------------------
# Configuration
# -----------------------------

# Laptop IP (same as in tcp_button_sender.py). Used to label direction.
LAPTOP_IP = "10.3.61.26"

# TCP port to sniff. Default 5005 (plain TCP); use 5006 for TLS demo.
TCP_PORT = 5005

# Network interface to sniff on. None = default (often "eth0" or "wlan0" on UNIHIKER).
# Set to a specific name, e.g. "eth0", if you want to limit to one interface.
IFACE = None


def format_payload(data: bytes) -> str:
    """Try to show payload as text; fall back to repr if not UTF-8."""
    try:
        return data.decode("utf-8").strip()
    except UnicodeDecodeError:
        return repr(data)


def handle_packet(pkt) -> None:
    """Process one sniffed packet: print TCP payload with direction."""
    if not pkt.haslayer(TCP) or not pkt.haslayer(Raw):
        return
    ip = pkt[IP]
    tcp = pkt[TCP]
    if tcp.sport != TCP_PORT and tcp.dport != TCP_PORT:
        return
    payload = bytes(pkt[Raw].load)
    if not payload:
        return
    src = ip.src
    dst = ip.dst
    text = format_payload(payload)
    if src == LAPTOP_IP:
        direction = "<-- From Laptop"
    elif dst == LAPTOP_IP:
        direction = "--> To Laptop"
    else:
        direction = f"{src}:{tcp.sport} -> {dst}:{tcp.dport}"
    print(f"TCP {direction}: {text}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Sniff TCP traffic between UNIHIKER and laptop. Use --port 5006 for TLS."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5005,
        help="TCP port to sniff (default: 5005 for plain TCP, use 5006 for TLS)",
    )
    return parser.parse_args()


def main() -> None:
    global TCP_PORT
    args = parse_args()
    TCP_PORT = args.port
    print(f"Sniffing TCP on port {TCP_PORT} (Laptop = {LAPTOP_IP}). Ctrl+C to stop.")
    print("(Filtering in Python; no libpcap required.)")
    if IFACE:
        print(f"Interface: {IFACE}")
    print("-" * 60)
    try:
        sniff(prn=handle_packet, iface=IFACE, store=False)
    except Scapy_Exception as e:
        if "libpcap" in str(e).lower():
            print("Libpcap is required for sniffing on this system.", file=sys.stderr)
            print("Install it with: sudo apt-get install libpcap0.8", file=sys.stderr)
        else:
            print(f"Scapy error: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print("Permission denied. Try: sudo python3 sniff.py", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()