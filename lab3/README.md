# UNIHIKER–Laptop UDP/TCP Test Scripts

This folder contains small, educational Python scripts that demonstrate how to
send and receive messages between a UNIHIKER M10 single-board computer and a
laptop (or any regular computer), using either **UDP** or **TCP**.

## Files

### UDP (connectionless)

- `unihiker/udp_button_sender.py`  
  UNIHIKER-side script that:
  - draws two buttons on the UNIHIKER screen,
  - sends different UDP messages to the laptop when each button is pressed, and
  - listens for ACK (acknowledgement) messages from the laptop in a
    background thread and shows them on the screen.

- `laptop/udp_receiver.py`  
  Laptop-side script that:
  - listens on a UDP port for messages from the UNIHIKER,
  - prints each incoming message to the terminal, and
  - sends an ACK message back to the UNIHIKER for each message received.

### TCP (connection-oriented)

- `unihiker/tcp_button_sender.py`  
  Same behaviour as the UDP sender, but over a persistent TCP connection:
  - connects to the laptop on first button press (or reconnects if the link drops),
  - sends button messages over the same connection, and
  - a background thread receives ACKs on that connection.

- `laptop/tcp_receiver.py`  
  TCP server that:
  - listens for one TCP connection at a time,
  - prints each message received and sends an ACK back over the same connection,
  - after the client disconnects, accepts the next connection.

### TCP with TLS (encrypted)

- `unihiker/tcp_button_sender_tls.py`  
  Same behaviour as the plain TCP sender, but traffic is encrypted with TLS.
  Requires a server certificate for verification; see the TLS section below.

- `laptop/tcp_receiver_tls.py`  
  TLS-wrapped TCP server (listens on port 5006 by default). Requires a
  certificate and private key; see the TLS section below for setup.

### Sniffer (UNIHIKER only)

- `unihiker/sniff.py`  
  Uses Scapy to sniff TCP traffic between the UNIHIKER and the laptop.
  Prints every TCP payload with direction (--> To Laptop / <-- From Laptop).
  Use `--port 5005` for plain TCP (default) or `--port 5006` for TLS. With plain
  TCP you will see readable messages; with TLS, payloads are encrypted and
  appear as gibberish. Requires `scapy` and usually root: `sudo python3 sniff.py`.
  On the UNIHIKER you may need: `sudo apt-get install libpcap0.8`. Set
  `LAPTOP_IP` (and optionally `IFACE`) to match your setup.

All scripts are heavily commented line by line to explain what each part
does and to make them suitable as teaching examples.

## Configuration

1. **Network**
   - Make sure the UNIHIKER M10 and your laptop are connected to the same
     network (for example, the same Wi‑Fi router).
   - Find the IP address of your laptop on that network (for example,
     `192.168.1.100`).

2. **UNIHIKER script (`unihiker/udp_button_sender.py`)**
   - Open the script and set the `LAPTOP_IP` constant near the top of the
     file to your laptop's actual IP address.
   - The default UDP port is `5005`. If you change this value, you must
     use the same port number in the laptop script.

3. **Laptop script (`laptop/udp_receiver.py`)**
   - By default, the script listens on UDP port `5005`.
   - You can override the port with a command-line option, for example:
     `python3 udp_receiver.py --port 6000`
     (if you change it, also update `LAPTOP_PORT` in the UNIHIKER script).

The same port and `LAPTOP_IP` settings apply to the **TCP** scripts
(`tcp_button_sender.py` and `tcp_receiver.py`). Run the laptop TCP receiver first,
then the UNIHIKER TCP sender; the UNIHIKER connects on first button press.

## How to Run

1. **On the laptop**
   - Open a terminal.
   - Change into the `tcp_udp_test/laptop` directory.
   - Run:
     - `python3 udp_receiver.py`
   - The script will print a line such as:
     - `Listening for UDP on 0.0.0.0:5005 (Ctrl+C to stop)`
   - Leave this terminal window open so it can receive messages.

2. **On the UNIHIKER M10**
   - Copy `unihiker/udp_button_sender.py` onto the UNIHIKER (for example,
     using VS Code, Thonny, or file sharing as described in the UNIHIKER
     documentation at `https://www.unihiker.com/wiki/`).
   - Edit `LAPTOP_IP` in the script so it matches your laptop's IP.
   - Run the script using your preferred method (VS Code, Jupyter,
     Python IDLE, or the terminal).
   - The UNIHIKER screen will show two buttons:
     - **Send from Button 1**
     - **Send from Button 2**

3. **Testing the connection**
   - Press **Send from Button 1** on the UNIHIKER.
     - The laptop terminal should print a line showing it received a
       message from the UNIHIKER.
     - Shortly after, the UNIHIKER screen should update to show an
       `ACK` message from the laptop.
   - Press **Send from Button 2** to send a different message and see
     the same round-trip behaviour.

If you do not see messages or ACKs, check:
- that the laptop IP address in `LAPTOP_IP` is correct,
- that the UDP port number matches in both scripts, and
- that any firewall on the laptop allows incoming UDP traffic on that port.

---

## TLS (Encrypted) TCP Demo

The TLS versions encrypt all traffic so that a packet sniffer cannot read the
message contents. This section explains how to create a self-signed certificate,
configure the scripts, and run the sniffing demonstration.

### Self-Signed Certificate Creation

**Where to run OpenSSL:** Run `openssl` on your **laptop** (the machine that runs
`tcp_receiver_tls.py`). The certificate and private key will stay on the laptop;
only the public certificate (`server.crt`) is copied to the UNIHIKER.

**Prerequisites:** You need OpenSSL installed. See platform notes below.

1. Open a terminal (or Command Prompt / PowerShell on Windows).
2. Change into your project directory. For example, if your project is at
   `C:\Users\me\tcp_udp_test` (Windows) or `~/tcp_udp_test` (Mac/Linux):
   - **Mac/Linux:** `cd ~/tcp_udp_test` (or your actual path)
   - **Windows:** `cd C:\Users\me\tcp_udp_test` (or your actual path)
3. Create the `certs` folder and generate the certificate:

**macOS and Linux** (OpenSSL is usually pre-installed):

```bash
mkdir -p certs
cd certs
openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 365 -nodes \
  -subj "/CN=localhost" -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"
```

**Windows** (OpenSSL is not pre-installed; choose one option):

- **Option A – Git for Windows:** If you have Git installed, open "Git Bash" and run
  the same commands as above; Git Bash includes OpenSSL.

- **Option B – Install OpenSSL:** Download the installer from
  [Win32 OpenSSL](https://slproweb.com/products/Win32OpenSSL.html) (e.g. "Win64
  OpenSSL v3.x Light"), install it, then open a new Command Prompt or PowerShell
  and run (adjust paths if your project lives elsewhere):

  ```cmd
  mkdir certs
  cd certs
  "C:\Program Files\OpenSSL-Win64\bin\openssl.exe" req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 365 -nodes -subj "/CN=localhost" -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"
  ```

- **Option C – WSL:** If you use WSL (Windows Subsystem for Linux), run the
  same commands as the Mac/Linux section in a WSL terminal.

**For LAN use (UNIHIKER and laptop on same network):** Include your laptop's IP
in the certificate so the UNIHIKER can verify it. Replace `10.3.61.26` with
your laptop's actual IP address:

**macOS and Linux:**
```bash
openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 365 -nodes \
  -subj "/CN=10.3.61.26" -addext "subjectAltName=IP:10.3.61.26,DNS:localhost"
```

**Windows (Git Bash or WSL):** Same command as above. For native Windows with
OpenSSL installed, use the long form shown in Option B but with the updated
`-subj` and `-addext` values.

**Output files:**
- **server.crt** – public certificate; copy this to the UNIHIKER for verification.
- **server.key** – private key; keep this **only on the laptop**; never share it.

### Certificate Configuration

**On the laptop (tcp_receiver_tls.py):**
- Place `server.crt` and `server.key` in `tcp_udp_test/certs/`.
- The default `--cert` and `--key` paths point to `certs/server.crt` and
  `certs/server.key`. Override if needed:
  `python3 tcp_receiver_tls.py --cert /path/to/server.crt --key /path/to/server.key`

**On the UNIHIKER (tcp_button_sender_tls.py):**
- Copy `server.crt` to the UNIHIKER (e.g. alongside the script or in `certs/`).
- Edit `CERT_FILE` in the script to point to the certificate path, for example:
  `CERT_FILE = "/home/pi/tcp_udp_test/certs/server.crt"`
  Or use the default relative path if the project layout is preserved.

### How to Run the TLS Demo

1. **On the laptop:** Start the TLS receiver (default port 5006):
   ```bash
   cd tcp_udp_test/laptop
   python3 tcp_receiver_tls.py
   ```

2. **On the UNIHIKER:** Run `tcp_button_sender_tls.py` with `LAPTOP_IP` and
   `CERT_FILE` configured. Press the buttons; messages and ACKs work as with
   plain TCP, but traffic is encrypted.

### Sniffing Demonstration

Run `sniff.py` on the UNIHIKER while using either plain TCP or TLS:

| Scenario      | Commands | Sniff output |
| ------------- | -------- | ------------ |
| **Plain TCP** | Laptop: `tcp_receiver.py`, UNIHIKER: `tcp_button_sender.py`, UNIHIKER: `sudo python3 sniff.py` (or `--port 5005`) | Readable: `UNIHIKER_M10: BUTTON_1_PRESSED`, `ACK: ...` |
| **TLS**       | Laptop: `tcp_receiver_tls.py`, UNIHIKER: `tcp_button_sender_tls.py`, UNIHIKER: `sudo python3 sniff.py --port 5006` | Encrypted bytes / gibberish; messages cannot be read |

With plain TCP, sniff.py shows the actual message content. With TLS, sniff.py
shows only encrypted payloads; an eavesdropper cannot read the button messages
or ACKs.