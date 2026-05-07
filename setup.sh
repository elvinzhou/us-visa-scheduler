#!/bin/bash
# Oracle Cloud Ubuntu 22.04 bootstrap — run once after provisioning the VM.
# Sets up: Xfce desktop, TigerVNC, noVNC (browser-accessible), Chrome/Chromium,
# Python deps, OS firewall, and systemd services for auto-start on reboot.
#
# Usage (from Oracle Cloud Shell or any SSH session):
#   chmod +x setup.sh && ./setup.sh
#
# After it finishes, open port 6080 in your OCI Security List (instructions printed at end).
set -euo pipefail

echo "=== US Visa Scheduler — Oracle Cloud Setup ==="
echo

# ── VNC password ──────────────────────────────────────────────────────────────
while true; do
    read -s -p "Set a VNC password (6–8 chars): " VNC_PASS; echo
    read -s -p "Confirm VNC password: "           VNC_PASS2; echo
    [ "$VNC_PASS" = "$VNC_PASS2" ] && break
    echo "Passwords do not match, try again."
done

# ── 1. System update ──────────────────────────────────────────────────────────
echo
echo "[1/6] Updating system packages..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# ── 2. Desktop + VNC ─────────────────────────────────────────────────────────
echo "[2/6] Installing Xfce desktop and TigerVNC..."
sudo apt-get install -y -qq xfce4 xfce4-terminal tigervnc-standalone-server

mkdir -p ~/.vnc

# Write VNC password non-interactively
printf "%s\n%s\nn\n" "$VNC_PASS" "$VNC_PASS" | vncpasswd

# VNC startup script — launch Xfce
cat > ~/.vnc/xstartup << 'XSTARTUP'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec startxfce4
XSTARTUP
chmod +x ~/.vnc/xstartup

# ── 3. noVNC ──────────────────────────────────────────────────────────────────
echo "[3/6] Installing noVNC..."
sudo apt-get install -y -qq novnc websockify

# ── 4. Chrome / Chromium ─────────────────────────────────────────────────────
echo "[4/6] Installing browser..."
ARCH=$(dpkg --print-architecture)
if [ "$ARCH" = "amd64" ]; then
    # Add Google's apt repo — more reliable than downloading the .deb directly
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
        | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
http://dl.google.com/linux/chrome/deb/ stable main" \
        | sudo tee /etc/apt/sources.list.d/google-chrome.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq google-chrome-stable
else
    # ARM — use Chromium from apt
    sudo apt-get install -y -qq chromium-browser chromium-chromedriver
    echo
    echo "  NOTE (ARM): undetected_chromedriver targets Google Chrome by default."
    echo "  If the scheduler fails to launch a browser, set these env vars in your .env:"
    echo "    UC_BROWSER_PATH=/usr/bin/chromium-browser"
    echo "    UC_DRIVER_PATH=/usr/bin/chromedriver"
    echo
fi

# ── 5. Python deps + tmux ────────────────────────────────────────────────────
echo "[5/6] Installing Python dependencies..."
sudo apt-get install -y -qq python3-pip python3-venv python3-full tmux
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 -m venv "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt"

# ── 6. Systemd services ───────────────────────────────────────────────────────
echo "[6/6] Creating systemd services and enabling OS firewall..."

# VNC — binds only to localhost; noVNC proxies it externally
sudo tee /etc/systemd/system/vncserver@.service > /dev/null << EOF
[Unit]
Description=TigerVNC server on display :%i
After=network.target

[Service]
Type=forking
User=$USER
ExecStartPre=-/usr/bin/vncserver -kill :%i
ExecStart=/usr/bin/vncserver :%i -geometry 1280x800 -depth 24 -localhost yes
ExecStop=/usr/bin/vncserver -kill :%i
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# noVNC — the only externally exposed port (6080)
sudo tee /etc/systemd/system/novnc.service > /dev/null << EOF
[Unit]
Description=noVNC WebSocket proxy
After=vncserver@1.service

[Service]
Type=simple
User=$USER
ExecStart=/usr/bin/websockify --web /usr/share/novnc/ 6080 localhost:5901
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vncserver@1 novnc
sudo systemctl start vncserver@1 novnc

# OS firewall — allow only noVNC (VNC itself is localhost-only)
sudo ufw allow 6080/tcp comment 'noVNC browser desktop'
sudo ufw allow OpenSSH
sudo ufw --force enable

# ── Done ──────────────────────────────────────────────────────────────────────
PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me || echo "<your-vm-public-ip>")

echo
echo "════════════════════════════════════════════════════════"
echo "  Setup complete!"
echo
echo "  Desktop URL:  http://$PUBLIC_IP:6080/vnc.html"
echo "  VNC password: the one you just set"
echo
echo "  REQUIRED: open port 6080 in the OCI Security List:"
echo "    OCI Console → Networking → Virtual Cloud Networks"
echo "    → your VCN → Security Lists → Default Security List"
echo "    → Add Ingress Rule:"
echo "      Source CIDR : 0.0.0.0/0  (or restrict to your IP: $(curl -s --max-time 5 ifconfig.me)/32)"
echo "      IP Protocol : TCP"
echo "      Dest Port   : 6080"
echo
echo "  To run the scheduler (copy .env.example → .env and fill it in first):"
echo "    tmux new -s visa"
echo "    source .venv/bin/activate"
echo "    python3 main.py"
echo "    # complete login in the browser desktop tab, press Enter, then"
echo "    # detach tmux with Ctrl+B D — the script keeps running"
echo "════════════════════════════════════════════════════════"
