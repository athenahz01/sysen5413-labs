# REST API Lab for IoT Course

This lab has two parts: a **server** that runs on your laptop and a **client** that runs on a UniHiker M10 single-board computer. The goal is to teach REST API design and the HTTP request/response cycle. The client reads the UniHiker’s onboard accelerometer (IMU), sends readings to the server, and the server computes orientation (roll/pitch) and logs the data.

## Components

- **server.py** — Flask app on the laptop. Listens on `0.0.0.0:5000` so the UniHiker can reach it over Wi‑Fi.
- **client.py** — Runs on the UniHiker M10. Uses the pinpong library to read the IMU and the requests library to talk to the server.
- **sensor_log.txt** — Created by the server in the same directory as `server.py`; one line of JSON per POST to `/data`.

---

## Setup

### On the laptop (server)

1. Install Python 3 and pip if needed.
2. Install Flask:
   ```bash
   pip install flask
   ```
   Or use the project requirements:
   ```bash
   pip install -r requirements-server.txt
   ```
3. From the `rest_api_lab` directory, run:
   ```bash
   python server.py
   ```
   Or: `python3 server.py`  
   You should see Flask listening on `0.0.0.0:5000`.

### On the UniHiker M10 (client)

1. Ensure Python 3 is available on the UniHiker (Debian Linux).
2. Install the required libraries:
   ```bash
   pip install requests pinpong
   ```
   Or:
   ```bash
   pip install -r requirements-client.txt
   ```
   (Pinpong may have platform-specific install notes for the UniHiker; check the [UniHiker documentation](https://www.unihiker.com/wiki/) if needed.)
3. Copy `client.py` (and optionally the requirements file) to the UniHiker.
4. Run the client, passing your **laptop’s IP address** on the same Wi‑Fi network:
   ```bash
   python client.py 192.168.1.42
   ```
   If you omit the IP, it defaults to `127.0.0.1` (for testing when server and client run on the same machine).

---

## Finding your laptop’s IP address

The UniHiker must use the laptop’s IP on the **same Wi‑Fi network** (e.g. your lab router).

- **macOS**  
  - **GUI:** System Preferences → Network → Wi‑Fi → Advanced → TCP/IP; note “IP Address”.  
  - **Terminal:**  
    ```bash
    ipconfig getifaddr en0
    ```  
    (Use `en0` for typical Wi‑Fi; if that’s empty, try `en1` or run `ifconfig` and look at the interface that has your Wi‑Fi address.)

- **Linux**  
  ```bash
  ip addr
  ```  
  or  
  ```bash
  hostname -I
  ```  
  Look at the interface that corresponds to your Wi‑Fi (e.g. `wlan0`). Use the IPv4 address (e.g. `192.168.1.100`).

- **Windows**  
  Open Command Prompt or PowerShell and run:  
  ```bash
  ipconfig
  ```  
  Find the “Wireless LAN adapter” (or similar) and use the “IPv4 Address” (e.g. `192.168.1.100`).

---

## Firewall (Linux laptops)

If the UniHiker cannot connect to the server, the laptop firewall may be blocking port 5000. On Linux with **ufw**:

```bash
sudo ufw allow 5000
sudo ufw status
```

This allows inbound TCP traffic on port 5000 so the UniHiker can reach the Flask server. Reload or restart the server after changing the firewall if needed.

---

## API endpoints

All endpoints use **JSON** for request and response bodies where applicable. All responses (including errors) use `Content-Type: application/json`.

| Method | Path          | Request body (if any)                                                                 | Response body |
|--------|---------------------------------------------------------------------------------------|----------------|
| POST   | `/orientation` | `{"ax": <float>, "ay": <float>, "az": <float>}` (raw accelerometer; required)        | `{"roll": <float>, "pitch": <float>}` in degrees, or `{"error": "..."}` with 400 |
| POST   | `/data`        | Arbitrary JSON object; at minimum `ax`, `ay`, `az`; client often adds `client_timestamp` | `{"status": "ok", "rows_saved": <int>}` |
| GET    | `/data`        | —                                                                                     | JSON array of all logged records (one object per line in `sensor_log.txt`) |
| GET    | `/status`      | —                                                                                     | `{"status": "running", "uptime_seconds": <float>, "rows_logged": <int>}` |

- **POST /orientation**  
  Computes roll and pitch in degrees from `ax`, `ay`, `az`. Returns 400 with a JSON error if any of the three fields are missing or non-numeric.

- **POST /data**  
  Appends the JSON body as one line to `sensor_log.txt`, with a server-added `server_timestamp` (ISO 8601). Returns the total number of lines currently in the file as `rows_saved`. Writes are thread-safe (using a lock).

- **GET /data**  
  Returns all records from `sensor_log.txt` as a JSON array. If the file does not exist, returns `[]`.

- **GET /status**  
  Returns server status, uptime in seconds since start, and current line count of `sensor_log.txt` (`rows_logged`; 0 if the file does not exist).

---

## Testing from the laptop (optional)

With the server running on the laptop, you can try the API with `curl` before using the UniHiker.

```bash
# Health and metrics
curl -s http://127.0.0.1:5000/status

# Compute orientation (example values)
curl -s -X POST http://127.0.0.1:5000/orientation \
  -H "Content-Type: application/json" \
  -d '{"ax": 0.1, "ay": 0.2, "az": 9.8}'

# Log a sample (server adds server_timestamp)
curl -s -X POST http://127.0.0.1:5000/data \
  -H "Content-Type: application/json" \
  -d '{"ax": 0.1, "ay": 0.2, "az": 9.8, "client_timestamp": "2025-03-07T12:00:00Z"}'

# Get all logged records
curl -s http://127.0.0.1:5000/data
```

Use your laptop’s actual IP (e.g. `192.168.1.42`) instead of `127.0.0.1` when calling from another machine.

---

## How to run the lab

1. **Laptop:** Start the server: `python server.py` (or `python3 server.py`) from `rest_api_lab`.
2. **UniHiker:** Run the client with the laptop’s IP: `python client.py <laptop_ip>`.
3. The client will, every second, read the IMU, POST to `/orientation` (and print roll/pitch) and POST to `/data` (and print `rows_saved`). On **Ctrl+C** it exits and prints how many samples were sent.
4. If the server is unreachable, the client prints a warning and continues the loop instead of crashing.

Log file path: the server writes `sensor_log.txt` in the same directory as `server.py` (see `server.py` for the exact path logic).