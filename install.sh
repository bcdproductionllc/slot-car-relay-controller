#!/bin/bash
# Slot Car Relay Controller Installation Script
# Author: BCD Production LLC
# License: MIT

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Slot Car Relay Controller - Installation Script       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Get the actual user who ran sudo
ACTUAL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo ~$ACTUAL_USER)

echo "📋 Installation Summary:"
echo "   User: $ACTUAL_USER"
echo "   Home: $USER_HOME"
echo ""

# Update system
echo "🔄 Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

# Install dependencies
echo "📦 Installing dependencies..."
apt-get install -y python3 python3-pip python3-rpi.gpio network-manager

# Check if script file exists
if [ ! -f "smartrace_relay.py" ]; then
    echo "❌ Error: smartrace_relay.py not found in current directory"
    echo "   Please run this script from the repository directory"
    exit 1
fi

# Copy script
echo "📄 Installing script..."
cp smartrace_relay.py $USER_HOME/smartrace_relay.py
chmod +x $USER_HOME/smartrace_relay.py
chown $ACTUAL_USER:$ACTUAL_USER $USER_HOME/smartrace_relay.py

# Create config directory
mkdir -p $USER_HOME/.config
chown $ACTUAL_USER:$ACTUAL_USER $USER_HOME/.config

# Install systemd service
echo "⚙️  Installing systemd service..."
cat > /etc/systemd/system/smartrace-relay.service << EOF
[Unit]
Description=Slot Car Relay Controller
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$USER_HOME
ExecStart=/usr/bin/python3 $USER_HOME/smartrace_relay.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable service
echo "✅ Enabling service to start on boot..."
systemctl enable smartrace-relay.service

# Get IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              Installation Complete! 🎉                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Configure GPIO pins (if needed):"
echo "   sudo nano $USER_HOME/smartrace_relay.py"
echo "   Edit RELAY1_PIN and RELAY2_PIN"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl start smartrace-relay.service"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status smartrace-relay.service"
echo ""
echo "4. Access web interface:"
echo "   http://$IP_ADDRESS:9090"
echo ""
echo "5. Configure SmartRace:"
echo "   Settings → Data Interface"
echo "   Endpoint: http://$IP_ADDRESS:9091"
echo ""
echo "6. View logs:"
echo "   sudo journalctl -u smartrace-relay.service -f"
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  For documentation, visit the GitHub repository README     ║"
echo "║  https://github.com/bcdproductionllc/slot-car-relay-controller"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Ask if user wants to start now
read -p "Start the service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl start smartrace-relay.service
    sleep 2
    systemctl status smartrace-relay.service
    echo ""
    echo "✅ Service started! Access web interface at: http://$IP_ADDRESS:9090"
fi
