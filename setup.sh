#!/bin/bash
# Local setup for WSL2 (Windows 11 / WSLg), Raspberry Pi, or Ubuntu desktop/server.
# Installs Chrome/Chromium, Python venv, and tmux — no VNC or remote desktop needed.
#
# Usage:
#   chmod +x setup.sh && ./setup.sh
set -euo pipefail

echo "=== US Visa Scheduler — Local Setup ==="
echo

# ── 1. System update ──────────────────────────────────────────────────────────
echo "[1/3] Updating system packages..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# ── 2. Chrome / Chromium ──────────────────────────────────────────────────────
echo "[2/3] Installing browser..."
ARCH=$(dpkg --print-architecture)
if [ "$ARCH" = "amd64" ]; then
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
        | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
http://dl.google.com/linux/chrome/deb/ stable main" \
        | sudo tee /etc/apt/sources.list.d/google-chrome.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq google-chrome-stable
else
    # ARM (Raspberry Pi) — use Chromium from apt
    sudo apt-get install -y -qq chromium-browser chromium-chromedriver
    echo
    echo "  NOTE (ARM): undetected_chromedriver targets Google Chrome by default."
    echo "  If the scheduler fails to launch, add these to your .env:"
    echo "    UC_BROWSER_PATH=/usr/bin/chromium-browser"
    echo "    UC_DRIVER_PATH=/usr/bin/chromedriver"
    echo
fi

# ── 3. Python deps + tmux ─────────────────────────────────────────────────────
echo "[3/3] Installing Python dependencies and tmux..."
sudo apt-get install -y -qq python3-pip python3-venv python3-full tmux
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 -m venv "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt"

# ── Done ──────────────────────────────────────────────────────────────────────
echo
echo "════════════════════════════════════════════════════════"
echo "  Setup complete!"
echo
echo "  Next steps:"
echo "    1. cp .env.example .env && nano .env   (fill in your details)"
echo "    2. Edit main.py to set LOCATION_NAME and BOOKING_CONFIG"
echo "    3. Run the scheduler:"
echo "         tmux new -s visa"
echo "         source .venv/bin/activate"
echo "         python3 main.py"
echo "         # log in manually in the browser, press Enter, then"
echo "         # detach tmux with Ctrl+B D"
echo
echo "  WSL note: requires WSLg (Windows 11) for the browser window."
echo "  On Windows 10 WSL2, install an X server (e.g. VcXsrv) first"
echo "  and set DISPLAY=:0 before running."
echo "════════════════════════════════════════════════════════"
