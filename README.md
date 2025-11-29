# Slot Car Relay Controller

A Raspberry Pi-based relay controller that integrates with slot car racing apps (like SmartRace) to provide automated timing signals via dual relay outputs.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)

## ☕ Support This Project

If you find this project helpful, consider buying me a coffee!

[![Buy Me A Coffee](https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=&slug=bcdproduction&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff)](https://www.buymeacoffee.com/bcdproduction)

## 🎯 Features

- **Dual Relay Control**: Independent control of two relays for race start and end signals
- **Configurable Timing**: 
  - Adjustable relay pulse duration (0.1-5 seconds)
  - Configurable start delay for Relay 1 (0-30 seconds)
- **SmartRace Integration**: Receives VSC (Virtual Safety Car) events from SmartRace app
- **Web Interface**: 
  - Real-time relay status monitoring
  - Configuration management
  - WiFi network setup
  - Event logging
- **Auto-start**: Systemd service for automatic startup on boot
- **Debug Mode**: Comprehensive logging for troubleshooting

## 📋 Table of Contents

- [Hardware Requirements](https://github.com/bcdproductionllc/slot-car-relay-controller?tab=readme-ov-file#-hardware-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [SmartRace Setup](#smartrace-setup)
- [Web Interface](#web-interface)
- [Troubleshooting](#troubleshooting)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## 🔧 Hardware Requirements

### Required Components

1. **Raspberry Pi** (any model with GPIO)
   - Tested on: Raspberry Pi 2W, 3B+, 4B
   - Raspberry Pi OS (Bookworm or later recommended)

2. **Relay Module** (4-channel recommended)
   - Recommended: SRD-05VDC-SL-C 4-channel relay module by Inland(Comes with a shield)
   - Supports up to 10A @ 250VAC or 10A @ 30VDC
   - Available from various electronics suppliers

3. **Power Supply**
   - 5V 1.0A minimum for Raspberry Pi 2W
   - Additional power for relay loads if needed

4. **Jumper Wires**
   - Female-to-female jumper wires for GPIO connections

### Wiring Diagram

```
Raspberry Pi GPIO → Relay Module
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GPIO 4    → J2 (Relay 1 - Start Signal)
GPIO 22   → J3 (Relay 2 - End Signal)
GND       → GND
5V        → VCC
```

**Default GPIO Pin Mapping:**
- **Relay 1 (Start)**: GPIO 4 (Physical Pin 7)
- **Relay 2 (End)**: GPIO 22 (Physical Pin 15)

Alternative pins available: GPIO 6, GPIO 26

**Relay Module Pin Reference:**
```
Physical Board Layout:
┌─────────────────┐
│ J2  → GPIO 4    │ Top
│ J3  → GPIO 22   │
│ J4  → GPIO 6    │
│ J5  → GPIO 26   │ Bottom
└─────────────────┘
```

## 📥 Installation

### Quick Install

```bash
# Clone the repository
git clone https://github.com/bcdproductionllc/slot-car-relay-controller.git
cd slot-car-relay-controller

# Run the installation script
chmod +x install.sh
sudo ./install.sh
```

### Manual Installation

1. **Update System**
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

2. **Install Dependencies**
```bash
sudo apt-get install -y python3 python3-pip python3-rpi.gpio
```

3. **Copy Script**
```bash
sudo cp smartrace_relay.py /home/admin/smartrace_relay.py
sudo chmod +x /home/admin/smartrace_relay.py
```

4. **Create Systemd Service**
```bash
sudo cp smartrace-relay.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smartrace-relay.service
sudo systemctl start smartrace-relay.service
```

5. **Verify Installation**
```bash
sudo systemctl status smartrace-relay.service
```

## ⚙️ Configuration

### GPIO Pin Configuration

Edit the pin assignments in `smartrace_relay.py`:

```python
# Configuration
RELAY1_PIN = 4   # Start signal relay (GPIO BCM numbering)
RELAY2_PIN = 22  # End signal relay (GPIO BCM numbering)
```

### Port Configuration

Default ports:
- Web Interface: `9090`
- SmartRace Data Interface: `9091`

To change ports, edit:
```python
WEB_SERVER_PORT = 9090
SMARTRACE_DATA_PORT = 9091
```

### Timing Configuration

Access the web interface to configure:
- **Pulse Duration**: How long relays stay ON (0.1-5 seconds)
- **Relay 1 Delay**: Delay before Relay 1 activates (0-30 seconds)

Configuration is saved to `/home/admin/smartrace_config.json`

## 🚀 Usage

### Starting the Service

```bash
# Start the service
sudo systemctl start smartrace-relay.service

# Stop the service
sudo systemctl stop smartrace-relay.service

# Restart the service
sudo systemctl restart smartrace-relay.service

# Check status
sudo systemctl status smartrace-relay.service

# View live logs
sudo journalctl -u smartrace-relay.service -f
```

### Manual Operation

Run directly for testing:
```bash
sudo python3 /home/admin/smartrace_relay.py
```

Press `Ctrl+C` to stop.

## 📱 SmartRace Setup

### ⚖️ Disclaimer

This is an independent, unofficial project and is not affiliated with, endorsed by, or connected to SmartRace or its developers. SmartRace is a trademark of Marc Scheib.

### Configure SmartRace App

1. Open **SmartRace** on your iPad/iPhone
2. Go to **Settings** → **Data Interface**
3. Configure endpoint:
   - **URL**: `http://YOUR_RASPBERRY_PI_IP:9091`
   - Example: `http://192.168.1.100:9091`
4. Enable **VSC Events**
5. Save settings

### Find Your Raspberry Pi IP Address

On the Raspberry Pi:
```bash
hostname -I
```

Or check the web interface startup message.

### Testing the Connection

1. Press the **VSC button** in SmartRace
2. **Relay 1** should pulse immediately (or after configured delay)
3. Wait for the countdown to reach 0
4. **Relay 2** should pulse when timer expires

## 🌐 Web Interface

Access the web interface at: `http://YOUR_RASPBERRY_PI_IP:9090`

### Features

- **Relay Status Dashboard**: Real-time status of both relays
- **Manual Relay Testing**: Test pulse buttons for each relay
- **Timing Configuration**: Adjust pulse duration and start delay
- **VSC Status Monitor**: View current VSC state and countdown
- **Event Log**: Last 5 SmartRace events received
- **System Information**: Network status, uptime, current time
- **WiFi Configuration**: Connect to different WiFi networks

### Screenshots

#### Main Dashboard
Shows relay status, configuration options, and event logs.

#### WiFi Configuration
Scan and connect to available WiFi networks with DHCP or static IP.

## 🐛 Troubleshooting

### Relay Not Triggering

**Check GPIO Pins:**
```bash
# Test individual relay
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(4, GPIO.OUT); GPIO.output(4, GPIO.HIGH); import time; time.sleep(1); GPIO.output(4, GPIO.LOW); GPIO.cleanup()"
```

**Verify Wiring:**
- Ensure GND and VCC are connected
- Check GPIO pin numbers match your configuration
- Verify relay module is powered

**Check Logs:**
```bash
sudo journalctl -u smartrace-relay.service -n 100
```

### SmartRace Not Connecting

**Verify Network:**
- Raspberry Pi and iPad must be on the same network
- Check firewall settings
- Ping test: `ping YOUR_IPAD_IP`

**Check Port Availability:**
```bash
sudo lsof -i :9091
```

**Test Endpoint:**
```bash
curl -X POST http://localhost:9091 -H "Content-Type: application/json" -d '{"event_type":"race.vsc_deployed","event_data":{"event_id":123},"time":1234567890}'
```

### Service Won't Start

**Check for Syntax Errors:**
```bash
python3 -m py_compile /home/admin/smartrace_relay.py
```

**Check Dependencies:**
```bash
python3 -c "import RPi.GPIO; print('GPIO OK')"
```

**View Full Logs:**
```bash
sudo journalctl -u smartrace-relay.service --no-pager -n 200
```

### Common Issues

| Problem | Solution |
|---------|----------|
| Address already in use | Kill old process: `sudo pkill -9 python3` |
| Permission denied | Run with sudo: `sudo python3 smartrace_relay.py` |
| GPIO warnings | Add `GPIO.setwarnings(False)` in setup_gpio() |
| Wrong event type | Check debug output for actual event type from SmartRace |

## 📡 API Documentation

### SmartRace Data Interface

**Endpoint:** `POST http://RASPBERRY_PI_IP:9091`

**Event Format:**
```json
{
  "event_type": "race.vsc_deployed",
  "event_data": {
    "event_id": 1234567890
  },
  "time": 1234567890000
}
```

**Supported Events:**
- `race.vsc_deployed` - VSC started (triggers Relay 1)
- `race.vsc_retracted` - VSC ended (triggers Relay 2 if manually retracted)

**Response:**
```json
{
  "status": "ok"
}
```

### Web Interface Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/wifi` | GET | WiFi configuration page |
| `/test1` | GET | Test pulse Relay 1 |
| `/test2` | GET | Test pulse Relay 2 |
| `/set-pulse` | POST | Update timing configuration |
| `/wifi/connect` | POST | Connect to WiFi network |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/bcdproductionllc/slot-car-relay-controller.git
cd slot-car-relay-controller

# Make changes
nano smartrace_relay.py

# Test changes
sudo python3 smartrace_relay.py

# Commit and push
git add .
git commit -m "Description of changes"
git push origin main
```

### Guidelines

- Follow PEP 8 style guide for Python code
- Test on actual hardware before submitting
- Update documentation for new features
- Add comments for complex logic

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- SmartRace app by Marc Scheib
- Raspberry Pi Foundation
- Python GPIO library contributors

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/bcdproductionllc/slot-car-relay-controller/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bcdproductionllc/slot-car-relay-controller/discussions)
- **Buy Me A Coffee**: https://www.buymeacoffee.com/bcdproduction

## 🔄 Changelog

### v1.0.0 (2025-10-30)
- Initial release
- Dual relay control with pulse mode
- SmartRace VSC event integration
- Web interface for configuration
- WiFi setup interface
- Configurable timing parameters
- Systemd service integration
- Debug logging

---

**Made with ❤️ for the slot car racing community**

[![Buy Me A Coffee](https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=&slug=bcdproduction&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff)](https://www.buymeacoffee.com/bcdproduction)
