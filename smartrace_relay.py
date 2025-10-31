#!/usr/bin/env python3
"""
SmartRace Relay Controller with Dual Relay Pulse Control
- Relay 1 (Pin 18): Pulses ON/OFF when VSC button is pressed (race start)
- Relay 2 (Pin 23): Pulses ON/OFF when VSC timer ends (race end)
- WiFi network selection from web interface
- DHCP or Static IP configuration
- Configurable pulse duration
"""

import socket
import time
import threading
import subprocess
import os
import sys
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import re

# Try to import RPi.GPIO
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    print("✅ GPIO library loaded")
except ImportError:
    GPIO_AVAILABLE = False
    print("❌ GPIO library not available - test mode")

# Configuration
RELAY1_PIN = 18  # Start signal relay
RELAY2_PIN = 23  # End signal relay
WEB_SERVER_PORT = 9090
SMARTRACE_DATA_PORT = 9091
CONFIG_FILE = '/home/admin/smartrace_config.json'

# Global state
relay1_state = False
relay2_state = False
server_running = False
startup_time = datetime.now()
vsc_active = False
vsc_end_time = None
last_smartrace_event = None
smartrace_events_log = []
current_network_config = {}
pulse_duration = 0.5  # Default pulse duration in seconds
relay1_delay = 5.0 #Delay before Relay 1 pulses (in seconds)

def load_config():
    """Load configuration from file"""
    global pulse_duration
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                pulse_duration = config.get('pulse_duration', 0.5)
                relay1_delay = config.get('relay1_delay', 5.0)
                print(f"✅ Loaded config: Pulse duration = {pulse_duration}s, Relay 1 delay = {relay1_delay}s")
    except Exception as e:
        print(f"⚠️ Config load error: {e}, using defaults")
        pulse_duration = 0.5

def save_config():
    """Save configuration to file"""
    try:
        config = {
            'pulse_duration': pulse_duration,
            'relay1_delay': relay1_delay
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Config saved: Pulse duration = {pulse_duration}s")
    except Exception as e:
        print(f"❌ Config save error: {e}")

def setup_gpio():
    """Setup GPIO for relay control"""
    global GPIO_AVAILABLE
    if GPIO_AVAILABLE:
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(RELAY1_PIN, GPIO.OUT)
            GPIO.setup(RELAY2_PIN, GPIO.OUT)
            GPIO.output(RELAY1_PIN, GPIO.LOW)
            GPIO.output(RELAY2_PIN, GPIO.LOW)
            print(f"✅ GPIO pins {RELAY1_PIN} and {RELAY2_PIN} configured")
            return True
        except Exception as e:
            print(f"❌ GPIO setup failed: {e}")
            GPIO_AVAILABLE = False
            return False
    return False

def pulse_relay(relay_pin, relay_name, source="Manual"):
    """Pulse a relay ON then OFF"""
    global relay1_state, relay2_state, pulse_duration
    
    if GPIO_AVAILABLE:
        try:
            # Turn relay ON
            GPIO.output(relay_pin, GPIO.HIGH)
            if relay_pin == RELAY1_PIN:
                relay1_state = True
            else:
                relay2_state = True
            print(f"🔌 {relay_name} ON (pulse start) by {source} at {datetime.now().strftime('%H:%M:%S')}")
            
            # Wait for pulse duration
            time.sleep(pulse_duration)
            
            # Turn relay OFF
            GPIO.output(relay_pin, GPIO.LOW)
            if relay_pin == RELAY1_PIN:
                relay1_state = False
            else:
                relay2_state = False
            print(f"🔌 {relay_name} OFF (pulse end) by {source} at {datetime.now().strftime('%H:%M:%S')}")
            
            return True
        except Exception as e:
            print(f"❌ Relay pulse error: {e}")
            return False
    else:
        print(f"🧪 Test - {relay_name} PULSE by {source}")
        return True

def pulse_relay_threaded(relay_pin, relay_name, source="Manual"):
    """Pulse a relay in a separate thread"""
    thread = threading.Thread(target=pulse_relay, args=(relay_pin, relay_name, source))
    thread.daemon = True
    thread.start()

def monitor_vsc_timer():
    """Monitor VSC timer and trigger Relay 2 when it ends"""
    global vsc_active, vsc_end_time
    
    while True:
        try:
            if vsc_active and vsc_end_time is not None:
                current_time = time.time()
                if current_time >= vsc_end_time:
                    print("⏰ VSC timer ended - triggering Relay 2 (End Signal)")
                    pulse_relay_threaded(RELAY2_PIN, "Relay 2", "VSC Timer End")
                    vsc_active = False
                    vsc_end_time = None
            time.sleep(0.1)  # Check every 100ms
        except Exception as e:
            print(f"❌ Timer monitor error: {e}")
            time.sleep(1)

def scan_wifi_networks():
    """Scan for available WiFi networks"""
    try:
        result = subprocess.run(['sudo', 'nmcli', 'dev', 'wifi', 'list'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            networks = []
            lines = result.stdout.split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        in_use = '*' in line
                        ssid = parts[1] if not in_use else parts[2]
                        signal = '0'
                        for part in parts:
                            if '%' in part:
                                signal = part.replace('%', '')
                                break
                        
                        networks.append({
                            'ssid': ssid,
                            'signal': signal,
                            'in_use': in_use
                        })
            return networks
        return []
    except Exception as e:
        print(f"❌ WiFi scan error: {e}")
        return []

def get_current_network_info():
    """Get current network configuration"""
    try:
        result = subprocess.run(['nmcli', 'con', 'show', '--active'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'wifi' in line.lower():
                    parts = line.split()
                    ssid = parts[0]
                    
                    ip_result = subprocess.run(['ip', 'addr', 'show', 'wlan0'], 
                                             capture_output=True, text=True)
                    ip_address = 'N/A'
                    for ip_line in ip_result.stdout.split('\n'):
                        if 'inet ' in ip_line:
                            ip_address = ip_line.strip().split()[1].split('/')[0]
                            break
                    
                    return {
                        'ssid': ssid,
                        'ip': ip_address,
                        'connected': True
                    }
        return {'ssid': 'Not Connected', 'ip': 'N/A', 'connected': False}
    except Exception as e:
        print(f"❌ Network info error: {e}")
        return {'ssid': 'Error', 'ip': 'N/A', 'connected': False}

def get_ip_address():
    """Get current IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "0.0.0.0"

def connect_to_wifi(ssid, password, use_dhcp=True, static_ip='', gateway='', dns='8.8.8.8'):
    """Connect to WiFi network with DHCP or static IP"""
    try:
        print(f"🔧 Connecting to {ssid}...")
        
        subprocess.run(['sudo', 'nmcli', 'con', 'delete', ssid], 
                      capture_output=True)
        
        result = subprocess.run([
            'sudo', 'nmcli', 'con', 'add',
            'type', 'wifi',
            'ifname', 'wlan0',
            'con-name', ssid,
            'autoconnect', 'yes',
            'ssid', ssid
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return False, f"Failed to create connection: {result.stderr}"
        
        result = subprocess.run([
            'sudo', 'nmcli', 'con', 'modify', ssid,
            'wifi-sec.key-mgmt', 'wpa-psk',
            'wifi-sec.psk', password
        ], capture_output=True, text=True)
        
        if not use_dhcp:
            result = subprocess.run([
                'sudo', 'nmcli', 'con', 'modify', ssid,
                'ipv4.addresses', static_ip,
                'ipv4.gateway', gateway,
                'ipv4.dns', dns,
                'ipv4.method', 'manual'
            ], capture_output=True, text=True)
        
        result = subprocess.run(['sudo', 'nmcli', 'con', 'up', ssid], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            time.sleep(2)
            return True, f"Connected successfully to {ssid}"
        else:
            return False, f"Connection failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Connection error: {str(e)}"

class SmartRaceDataHandler(BaseHTTPRequestHandler):
    """Handler for SmartRace data interface"""
    
    def do_POST(self):
        global vsc_active, last_smartrace_event, smartrace_events_log, vsc_end_time
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # DEBUG: Print raw data to see what SmartRace actually sends
            print("=" * 60)
            print("📥 RAW DATA FROM SMARTRACE:")
            print(post_data)
            print("=" * 60)
            
            data = json.loads(post_data)
            
            # DEBUG: Print parsed JSON structure
            print("📊 PARSED JSON STRUCTURE:")
            print(json.dumps(data, indent=2))
            print("=" * 60)
            
            event_type = data.get('event_type', '')
            
            # Also check if data is at root level (some apps structure differently)
            if not event_type:
                event_type = data.get('type', '')
            
            last_smartrace_event = {
                'time': datetime.now().strftime('%H:%M:%S'),
                'type': event_type,
                'data': data
            }
            
            smartrace_events_log.append(last_smartrace_event)
            if len(smartrace_events_log) > 100:
                smartrace_events_log.pop(0)
            
            print(f"📡 SmartRace event type detected: '{event_type}'")
            
            # VSC Start - Pulse Relay 1
            # Check multiple possible event names
            if event_type in ['race.vsc_deployed', 'vscDeployed', 'vsc_deployed', 'vsc_started', 'VSC_DEPLOYED']:
                vsc_data = data.get('event', {}).get('data', {})
                if not vsc_data:
                    vsc_data = data.get('data', {})
                
                duration = vsc_data.get('duration', 60)  # Default 60 seconds
                
                print(f"🏁 VSC DEPLOYED - Duration: {duration}s")
                print(f"   → Triggering Relay 1 (Start Signal)")
                
                # Pulse Relay 1 immediately (start signal)
                print(f"⏳ Waiting {relay1_delay}s before triggering Relay 1...")
                time.sleep(relay1_delay)
                pulse_relay_threaded(RELAY1_PIN, "Relay 1", "VSC Start")
                
                # Set up timer for Relay 2 (end signal)
                vsc_active = True
                vsc_end_time = time.time() + duration
                
                print(f"   → Relay 2 will trigger in {duration}s at {datetime.fromtimestamp(vsc_end_time).strftime('%H:%M:%S')}")
            
            # VSC Withdrawn early - Cancel timer
            elif event_type in ['race.vsc_retracted', 'vsc_Withdrawn','vsc_withdrawn', 'vscEnded', 'vsc_ended', 'VSC_WITHDRAWN']:
                print(f"🏁 VSC WITHDRAWN - Cancelling timer")
                pulse_relay_threaded(RELAY2_PIN, "Relay 2", "VSC Manual Retract")
                vsc_active = False
                vsc_end_time = None
            else:
                print(f"⚠️ Unknown event type: '{event_type}' - no action taken")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            
        except Exception as e:
            print(f"❌ SmartRace data error: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

def wifi_config_page():
    """WiFi configuration page HTML"""
    networks = scan_wifi_networks()
    network_info = get_current_network_info()
    
    networks_html = ""
    for net in networks:
        signal_bars = "🟢" if int(net['signal']) > 70 else "🟡" if int(net['signal']) > 40 else "🔴"
        active = " (Connected)" if net['in_use'] else ""
        networks_html += f'<option value="{net["ssid"]}">{net["ssid"]} {signal_bars} {net["signal"]}%{active}</option>\n'
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFi Configuration</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif;
            background: #F2F2F7;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
        }}
        h1 {{
            color: #1C1C1E;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        .current-network {{
            background: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .form-group {{
            margin-bottom: 15px;
        }}
        label {{
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
            color: #1C1C1E;
        }}
        input, select {{
            width: 100%;
            padding: 12px;
            border: 1px solid #D1D1D6;
            border-radius: 10px;
            font-size: 16px;
            box-sizing: border-box;
        }}
        .radio-group {{
            display: flex;
            gap: 20px;
            margin-top: 10px;
        }}
        .radio-option {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .button {{
            width: 100%;
            padding: 14px;
            background: #007AFF;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 10px;
        }}
        .button:hover {{
            background: #0051D5;
        }}
        .back-link {{
            display: block;
            text-align: center;
            margin-top: 20px;
            color: #007AFF;
            text-decoration: none;
        }}
        .static-fields {{
            display: none;
            margin-top: 10px;
        }}
        .static-fields.visible {{
            display: block;
        }}
    </style>
    <script>
        function toggleIPMode() {{
            const mode = document.querySelector('input[name="ip_mode"]:checked').value;
            const staticFields = document.getElementById('staticFields');
            if (mode === 'static') {{
                staticFields.classList.add('visible');
            }} else {{
                staticFields.classList.remove('visible');
            }}
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>🌐 WiFi Configuration</h1>
        
        <div class="current-network">
            <strong>Current Network:</strong> {network_info['ssid']}<br>
            <strong>IP Address:</strong> {network_info['ip']}
        </div>
        
        <form method="POST" action="/wifi/connect" class="section">
            <div class="form-group">
                <label>WiFi Network</label>
                <select name="ssid" required>
                    {networks_html}
                </select>
            </div>
            
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            
            <div class="form-group">
                <label>IP Configuration</label>
                <div class="radio-group">
                    <div class="radio-option">
                        <input type="radio" id="dhcp" name="ip_mode" value="dhcp" checked onchange="toggleIPMode()">
                        <label for="dhcp" style="margin: 0">DHCP (Automatic)</label>
                    </div>
                    <div class="radio-option">
                        <input type="radio" id="static" name="ip_mode" value="static" onchange="toggleIPMode()">
                        <label for="static" style="margin: 0">Static IP</label>
                    </div>
                </div>
            </div>
            
            <div id="staticFields" class="static-fields">
                <div class="form-group">
                    <label>Static IP Address</label>
                    <input type="text" name="static_ip" placeholder="192.168.1.100/24">
                </div>
                <div class="form-group">
                    <label>Gateway</label>
                    <input type="text" name="gateway" placeholder="192.168.1.1">
                </div>
                <div class="form-group">
                    <label>DNS Server</label>
                    <input type="text" name="dns" value="8.8.8.8">
                </div>
            </div>
            
            <button type="submit" class="button">Connect</button>
        </form>
        
        <a href="/" class="back-link">← Back to Main</a>
    </div>
</body>
</html>"""
    return html

def web_page():
    """Main web interface HTML"""
    global relay1_state, relay2_state, vsc_active, vsc_end_time, pulse_duration
    
    uptime = datetime.now() - startup_time
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    
    current_ip = get_ip_address()
    network_info = get_current_network_info()
    
    relay1_status = "🟢 Active" if relay1_state else "⚫ Inactive"
    relay1_color = "#34C759" if relay1_state else "#8E8E93"
    
    relay2_status = "🟢 Active" if relay2_state else "⚫ Inactive"
    relay2_color = "#34C759" if relay2_state else "#8E8E93"
    
    vsc_status = "🟢 Running" if vsc_active else "⚫ Inactive"
    vsc_color = "#34C759" if vsc_active else "#8E8E93"
    
    vsc_time_remaining = ""
    if vsc_active and vsc_end_time is not None:
        remaining = max(0, int(vsc_end_time - time.time()))
        vsc_time_remaining = f" ({remaining}s remaining)"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartRace Relay Controller</title>
    <meta http-equiv="refresh" content="10">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        h1 {{
            color: white;
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        .subtitle {{
            color: rgba(255,255,255,0.9);
            font-size: 16px;
            margin-bottom: 30px;
        }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .section-title {{
            font-size: 20px;
            font-weight: 700;
            color: #1C1C1E;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .relay-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .relay-card {{
            background: #F2F2F7;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }}
        .relay-name {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 10px;
            color: #1C1C1E;
        }}
        .relay-pin {{
            font-size: 14px;
            color: #8E8E93;
            margin-bottom: 10px;
        }}
        .relay-status {{
            font-size: 16px;
            font-weight: 600;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 15px;
        }}
        .button-group {{
            display: flex;
            gap: 10px;
        }}
        .button {{
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            text-align: center;
            transition: all 0.3s;
        }}
        .button-test {{
            background: #007AFF;
            color: white;
        }}
        .button-test:hover {{
            background: #0051D5;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #F2F2F7;
        }}
        .info-row:last-child {{
            border-bottom: none;
        }}
        .info-label {{
            color: #8E8E93;
            font-weight: 500;
        }}
        .info-value {{
            color: #1C1C1E;
            font-weight: 600;
        }}
        .setup-info {{
            background: #FFF3CD;
            border: 2px solid #FFC107;
            padding: 20px;
            border-radius: 15px;
            margin-top: 20px;
            line-height: 1.8;
        }}
        .form-group {{
            margin-top: 20px;
        }}
        label {{
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #1C1C1E;
        }}
        input[type="number"] {{
            width: 100%;
            padding: 12px;
            border: 1px solid #D1D1D6;
            border-radius: 10px;
            font-size: 16px;
        }}
        .nav-button {{
            display: inline-block;
            padding: 12px 24px;
            background: white;
            color: #667eea;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏁 SmartRace Relay Controller</h1>
        <p class="subtitle">Dual Relay Pulse Control System</p>
        
        <a href="/wifi" class="nav-button">⚙️ WiFi Settings</a>
        
        <div class="section">
            <div class="section-title">🔌 Relay Status</div>
            <div class="relay-grid">
                <div class="relay-card">
                    <div class="relay-name">Relay 1 (Start)</div>
                    <div class="relay-pin">Pin {RELAY1_PIN}</div>
                    <div class="relay-status" style="background: {relay1_color}; color: white;">
                        {relay1_status}
                    </div>
                    <div class="button-group">
                        <a href="/test1" class="button button-test">Test Pulse</a>
                    </div>
                </div>
                
                <div class="relay-card">
                    <div class="relay-name">Relay 2 (End)</div>
                    <div class="relay-pin">Pin {RELAY2_PIN}</div>
                    <div class="relay-status" style="background: {relay2_color}; color: white;">
                        {relay2_status}
                    </div>
                    <div class="button-group">
                        <a href="/test2" class="button button-test">Test Pulse</a>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">⏱️ Pulse Configuration</div>
            <form method="POST" action="/set-pulse">
                <div class="form-group">
                    <label>Pulse Duration (seconds)</label>
                    <input type="number" name="pulse_duration" min="0.1" max="5" step="0.1" value="{pulse_duration}" required>
                    <div class="form-group">
                    <label>Relay 1 Start Delay (seconds)</label>
                    <input type="number" name="relay1_delay" min="0" max="30" step="0.5" value="{relay1_delay}" required>
                    <small style="color: #8E8E93; display: block; margin-top: 5px;">
                        Delay before Relay 1 pulses after VSC starts (0 to 30 seconds)
                    </small>
                </div>
                    <small style="color: #8E8E93; display: block; margin-top: 5px;">
                        Duration that relays stay ON during each pulse (0.1 to 5 seconds)
                    </small>
                </div>
                <button type="submit" class="button button-test" style="width: 100%; margin-top: 15px;">
                    💾 Save Pulse Duration
                </button>
            </form>
        </div>
        
        <div class="section">
            <div class="section-title">🏁 VSC Status</div>
            <div class="info-row">
                <span class="info-label">VSC Timer</span>
                <span class="info-value" style="color: {vsc_color};">{vsc_status}{vsc_time_remaining}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Last Event Type</span>
                <span class="info-value">{last_smartrace_event['type'] if last_smartrace_event else 'None'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Last Event Time</span>
                <span class="info-value">{last_smartrace_event['time'] if last_smartrace_event else 'N/A'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Events Received</span>
                <span class="info-value">{len(smartrace_events_log)}</span>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📜 Recent Events (Last 5)</div>
            {''.join([f'''
            <div class="info-row">
                <span class="info-label">{event['time']}</span>
                <span class="info-value">{event['type'] if event['type'] else 'Unknown'}</span>
            </div>
            ''' for event in smartrace_events_log[-5:][::-1]]) if smartrace_events_log else '<div style="color: #8E8E93; text-align: center; padding: 20px;">No events received yet</div>'}
            <div style="margin-top: 15px; padding: 10px; background: #FFF3CD; border-radius: 10px; font-size: 14px;">
                <strong>🔍 Debug Tip:</strong> Check the terminal/console output where the script is running. 
                When you press VSC, you should see raw JSON data printed. This will show exactly what SmartRace is sending.
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📡 System Information</div>
            <div class="info-row">
                <span class="info-label">WiFi Network</span>
                <span class="info-value">{network_info['ssid']}</span>
            </div>
            <div class="info-row">
                <span class="info-label">IP Address</span>
                <span class="info-value">{current_ip}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Uptime</span>
                <span class="info-value">{hours}h {minutes}m</span>
            </div>
            <div class="info-row">
                <span class="info-label">Current Time</span>
                <span class="info-value">{datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>
        
        <div class="setup-info">
            <strong>📱 SmartRace Setup Instructions:</strong><br>
            1. Open SmartRace app → Settings → Data Interface<br>
            2. Set Endpoint: <strong>http://{current_ip}:{SMARTRACE_DATA_PORT}</strong><br>
            3. Enable VSC events<br>
            4. Press VSC button to test:<br>
            &nbsp;&nbsp;&nbsp;• Relay 1 pulses ON/OFF immediately (race start)<br>
            &nbsp;&nbsp;&nbsp;• Relay 2 pulses ON/OFF when timer ends (race end)<br>
            <br>
            <strong>⚡ Relay Behavior:</strong><br>
            • Both relays pulse for {pulse_duration}s when triggered<br>
            • Relay 1: Triggered when VSC starts<br>
            • Relay 2: Triggered when VSC timer reaches 0
        </div>
    </div>
</body>
</html>"""
    return html

class WebHandler(BaseHTTPRequestHandler):
    """HTTP handler for web interface"""
    
    def do_GET(self):
        try:
            parsed_path = urlparse(self.path)
            
            if parsed_path.path == '/':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(web_page().encode())
                
            elif parsed_path.path == '/wifi':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(wifi_config_page().encode())
                
            elif parsed_path.path == '/test1':
                pulse_relay_threaded(RELAY1_PIN, "Relay 1", "Manual Test")
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                
            elif parsed_path.path == '/test2':
                pulse_relay_threaded(RELAY2_PIN, "Relay 2", "Manual Test")
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                
            else:
                self.send_response(404)
                self.end_headers()
                
        except Exception as e:
            print(f"❌ Web request error: {e}")
    
    def do_POST(self):
        global pulse_duration
        
        try:
            if self.path == '/wifi/connect':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                params = parse_qs(post_data)
                
                ssid = params.get('ssid', [''])[0]
                password = params.get('password', [''])[0]
                ip_mode = params.get('ip_mode', ['dhcp'])[0]
                
                use_dhcp = (ip_mode == 'dhcp')
                static_ip = params.get('static_ip', [''])[0]
                gateway = params.get('gateway', [''])[0]
                dns = params.get('dns', ['8.8.8.8'])[0]
                
                success, message = connect_to_wifi(ssid, password, use_dhcp, static_ip, gateway, dns)
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                
                status = "✅ Success!" if success else "❌ Failed"
                response = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connection Result</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif;
            background: #F2F2F7;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            max-width: 400px;
        }}
        h1 {{ color: {'#34C759' if success else '#FF3B30'}; }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background: #007AFF;
            color: white;
            text-decoration: none;
            border-radius: 10px;
            margin-top: 20px;
        }}
    </style>
    <meta http-equiv="refresh" content="5;url=/">
</head>
<body>
    <div class="container">
        <h1>{status}</h1>
        <p>{message}</p>
        <p>Redirecting in 5 seconds...</p>
        <a href="/" class="button">Go Back Now</a>
    </div>
</body>
</html>"""
                self.wfile.write(response.encode())
            
            elif self.path == '/set-pulse':
                global pulse_duration, relay1_delay
                
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                params = parse_qs(post_data)
                
                new_duration = float(params.get('pulse_duration', [0.5])[0])
                new_delay = float(params.get('relay1_delay', [5.0])[0])
                
                if 0.1 <= new_duration <= 5:
                    pulse_duration = new_duration
                if 0 <= new_delay <= 30:
                    relay1_delay = new_delay
                    
                save_config()
                print(f"✅ Settings saved: Pulse duration = {pulse_duration}s, Relay 1 delay = {relay1_delay}s")                
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                
        except Exception as e:
            print(f"❌ POST error: {e}")
    
    def log_message(self, format, *args):
        pass

def start_smartrace_data_server():
    """Start SmartRace data interface server"""
    try:
        server = HTTPServer(('0.0.0.0', SMARTRACE_DATA_PORT), SmartRaceDataHandler)
        print(f"✅ SmartRace data server started on port {SMARTRACE_DATA_PORT}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ SmartRace server error: {e}")

def start_web_server():
    """Start web interface server"""
    try:
        server = HTTPServer(('0.0.0.0', WEB_SERVER_PORT), WebHandler)
        print(f"✅ Web server started on port {WEB_SERVER_PORT}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Web server error: {e}")

def cleanup():
    """Cleanup on exit"""
    if GPIO_AVAILABLE:
        try:
            GPIO.cleanup()
            print("🧹 GPIO cleanup")
        except:
            pass

def main():
    """Main function"""
    print("🚀 Starting SmartRace Dual Relay Pulse Controller...")
    print(f"🐍 Python: {sys.version.split()[0]}")
    
    load_config()
    setup_gpio()
    
    print("⏳ Waiting for network...")
    time.sleep(5)
    
    current_ip = get_ip_address()
    network_info = get_current_network_info()
    
    print("=" * 60)
    print("🎯 SMARTRACE DUAL RELAY CONTROLLER STARTED")
    print("=" * 60)
    print(f"📡 Network: {network_info['ssid']}")
    print(f"🌐 IP Address: {current_ip}")
    print(f"📱 Web Interface: http://{current_ip}:{WEB_SERVER_PORT}")
    print(f"⚙️ WiFi Config: http://{current_ip}:{WEB_SERVER_PORT}/wifi")
    print(f"🔧 SmartRace Data: http://{current_ip}:{SMARTRACE_DATA_PORT}")
    print(f"🔌 Relay 1 (Start): GPIO {RELAY1_PIN}")
    print(f"🔌 Relay 2 (End): GPIO {RELAY2_PIN}")
    print(f"⏱️ Pulse Duration: {pulse_duration} seconds")
    print("=" * 60)
    print("📋 OPERATION:")
    print("   • VSC Start → Relay 1 pulses (race start signal)")
    print("   • VSC End → Relay 2 pulses (race end signal)")
    print("=" * 60)
    
    try:
        # Start VSC timer monitor thread
        timer_thread = threading.Thread(target=monitor_vsc_timer, daemon=True)
        timer_thread.start()
        
        # Start servers
        smartrace_thread = threading.Thread(target=start_smartrace_data_server, daemon=True)
        smartrace_thread.start()
        start_web_server()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        cleanup()

if __name__ == "__main__":
    main()
