#!/bin/bash
# Pi5 Dashboard Auto-Installer
# Detects hardware and installs only what's needed

set -e

echo "🥧 Raspberry Pi 5 Dashboard Installer"
echo "======================================"
echo ""

# Check if running on Pi 5
if ! grep -q "Raspberry Pi 5" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi 5"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Detect hardware
echo "🔍 Detecting hardware..."
HARDWARE_DETECTED=""

# Detect NVMe
if ls /dev/nvme* >/dev/null 2>&1; then
    echo "✓ NVMe SSD detected"
    HARDWARE_DETECTED="${HARDWARE_DETECTED}nvme,"
fi

# Detect SD Card
if [ -e /dev/mmcblk0 ]; then
    echo "✓ SD Card detected"
    HARDWARE_DETECTED="${HARDWARE_DETECTED}sd,"
fi

# Detect USB drives
if ls /dev/sd* >/dev/null 2>&1; then
    echo "✓ USB/SATA devices detected"
    HARDWARE_DETECTED="${HARDWARE_DETECTED}usb,"
fi

# Detect Hailo
if [ -e /dev/hailo0 ] || lsmod | grep -q hailo; then
    echo "✓ Hailo AI accelerator detected"
    HARDWARE_DETECTED="${HARDWARE_DETECTED}hailo,"
fi

# Check for Docker
if command -v docker >/dev/null 2>&1; then
    echo "✓ Docker already installed"
else
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

# Check for Scrypted
if docker ps 2>/dev/null | grep -q scrypted; then
    echo "✓ Scrypted container detected"
    HARDWARE_DETECTED="${HARDWARE_DETECTED}scrypted,"
fi

echo ""
echo "📊 Hardware Summary:"
echo "   Detected: ${HARDWARE_DETECTED:-none}"
echo ""

# Create directories
echo "📁 Creating directories..."
sudo mkdir -p /home/$USER/status-dashboard
sudo mkdir -p /etc/ssl/dashboard
sudo mkdir -p /nvme-backups 2>/dev/null || true
sudo mkdir -p /mnt/backup-ssd/backups 2>/dev/null || true
sudo mkdir -p /scrypted/nvr 2>/dev/null || true
# Ensure user owns working directories so copies succeed
sudo chown -R $USER:$USER /home/$USER/status-dashboard /nvme-backups /mnt/backup-ssd /scrypted 2>/dev/null || true

# Install dependencies
echo "📦 Installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip git curl

# Install Python packages
echo "🐍 Installing Python packages..."
pip3 install --break-system-packages psutil python-pam || pip3 install psutil python-pam

# Copy dashboard files from repo root (this installer lives in repo root)
echo "📥 Installing dashboard files..."
INSTALL_DIR="/home/$USER/status-dashboard"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

cp "$REPO_DIR"/index.html "$INSTALL_DIR/"
cp "$REPO_DIR"/stats_api.py "$INSTALL_DIR/"
cp "$REPO_DIR"/scrypted_stats.py "$INSTALL_DIR/"
cp "$REPO_DIR"/scrypted_update.js "$INSTALL_DIR/" 2>/dev/null || true
cp "$REPO_DIR"/scrypted_card.html "$INSTALL_DIR/" 2>/dev/null || true
cp "$REPO_DIR"/Dockerfile "$INSTALL_DIR/"
cp "$REPO_DIR"/docker-compose.yml "$INSTALL_DIR/"

# Copy scripts (expect them beside this installer in repo root under scripts/)
if [ -f "$REPO_DIR/scripts/backup-api-server.py" ]; then
    sudo cp "$REPO_DIR/scripts/backup-api-server.py" /home/$USER/
fi
if [ -f "$REPO_DIR/scripts/backup-restore-service.sh" ]; then
    sudo cp "$REPO_DIR/scripts/backup-restore-service.sh" /home/$USER/
    sudo chmod +x /home/$USER/backup-restore-service.sh
fi

# Setup SSL certificates
echo "🔐 Setting up SSL certificates..."
if [ ! -f /etc/ssl/dashboard/server.crt ]; then
    sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/ssl/dashboard/server.key \
        -out /etc/ssl/dashboard/server.crt \
        -subj "/C=US/ST=State/L=City/O=Pi5/CN=pi5-nvr"
    sudo chmod 644 /etc/ssl/dashboard/server.crt
    sudo chmod 600 /etc/ssl/dashboard/server.key
fi

# Setup backup API service (only if unit file exists alongside installer)
if [ -f "$REPO_DIR/config/backup-api.service" ]; then
    echo "⚙️  Setting up backup API service..."
    sudo cp "$REPO_DIR/config/backup-api.service" /etc/systemd/system/
    sudo sed -i "s/USER_PLACEHOLDER/$USER/g" /etc/systemd/system/backup-api.service
    sudo systemctl daemon-reload
    sudo systemctl enable backup-api.service
    sudo systemctl start backup-api.service
else
    echo "⚠️  Skipping backup API service setup (config/backup-api.service not found)"
fi

# Create .env from example if missing
cd "$INSTALL_DIR"
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
fi

# Build and start dashboard
echo "🐳 Building dashboard container..."
docker compose down 2>/dev/null || true
docker compose build
docker compose up -d

# Get IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ Installation Complete!"
echo ""
echo "📊 Dashboard URL: https://${IP_ADDR}:8443"
echo "🔑 Login with your SSH credentials (user: $USER)"
echo ""
echo "🔧 Hardware detected: ${HARDWARE_DETECTED:-none}"
echo ""
echo "📝 Next steps:"
echo "   1. Access dashboard in your browser"
echo "   2. Accept the self-signed SSL certificate"
echo "   3. Hardware tabs will auto-show based on detection"
echo ""
echo "💡 To update: ./update.sh"
echo "💡 To uninstall: ./uninstall.sh"
echo ""