# Prompt: BitbotV7 Raspberry Pi 3B Installation
Generated: 2026-03-29T23:00:00Z
Task Type: feature

---

## Context

### Project Overview
BitbotV7 is a Bitcoin trading bot with Flask web UI and REST API. This prompt covers deployment to Raspberry Pi 3B for testing and iterative development.

### Target Environment
- **Device**: Raspberry Pi 3 Model B (or compatible)
- **OS**: Raspberry Pi OS Lite (64-bit recommended) or full desktop
- **Python Version**: Python 3.9+ (pre-installed on modern Pi OS images)
- **Network**: Local WiFi/Ethernet connection from Windows development machine

### User Credentials
- SSH Username: `robbiegrant`
- SSH Password: `ktm990r-adv`
- Pi IP Address: `192.168.1.112`

---

## Task

Install and configure BitbotV7 on Raspberry Pi 3B for testing and continued development.

---

## Requirements

### Pre-requisites (Windows Side)
1. **SSH Client**: Windows has OpenSSH built-in (PowerShell `ssh` command)
2. **SCP Tool**: Available via OpenSSH or use WinSCP/Git Bash
3. **Project Files**: Complete BitbotV7 codebase in `C:\Projects\BitbotV7`

### Pre-requisites (Raspberry Pi Side)
1. **OS Installed**: Raspberry Pi OS with Python 3.9+
2. **SSH Enabled**: Must be enabled in OS configuration
3. **Network Access**: Pi must be reachable from Windows machine on same network
4. **Power Supply**: Stable 5V/2.5A minimum for Pi 3B

---

## Step-by-Step Installation Procedure

### Phase 1: SSH Connection Setup (Windows)

#### Fix Host Key Issue (First Connection After OS Reinstall)
```powershell
# Remove old host key entry if it exists
ssh-keygen -R "192.168.1.112"
```

#### Connect to Raspberry Pi
```powershell
ssh robbiegrant@192.168.1.112
# Password: ktm990r-adv
```

---

### Phase 2: System Preparation (On Raspberry Pi)

Once connected via SSH, run these commands on the Pi:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python dependencies and build tools
sudo apt install python3-pip python3-venv git build-essential libffi-dev -y

# Optional: Change default password if still using 'raspberry'
passwd
```

---

### Phase 3: Transfer Project Files (Windows)

Exit SSH on Pi (type `exit`), then from Windows PowerShell:

```powershell
# Copy entire project directory to Pi home folder
scp -r C:\Projects\BitbotV7 robbiegrant@192.168.1.112:~/
```

Wait for transfer to complete (may take 30-60 seconds depending on network speed).

---
### Phase 4: Virtual Environment Setup (On Raspberry Pi)

Connect back to SSH:
```bash
ssh robbiegrant@192.168.1.112
```

Then run these commands on the Pi:

```bash
# Navigate to project directory
cd ~/BitbotV7

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip inside virtual environment
pip install --upgrade pip

# Install production dependencies from requirements.txt
pip install -r requirements.txt
```

---

### Phase 5: Configuration (On Raspberry Pi)

```bash
# Copy example environment file
cp .env.example .env

# Edit the .env file with your Binance API keys
nano .env
```

**Required Environment Variables to Add:**

```bash
# Binance Testnet API Keys (for testing)
TESTNET_API_KEY=your_testnet_api_key_here
TESTNET_SECRET_KEY=your_testnet_secret_key_here

# Binance Live API Keys (for production trading - optional initially)
LIVE_API_KEY=
LIVE_SECRET_KEY=

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=<generate-a-random-secure-key>

# Bot Defaults
DEFAULT_MODE=testnet        # Use testnet for development/testing
DEFAULT_STYLE=scalping      # scalping | day_trading | swing_trading

# Trading Parameters
SYMBOL=BTCUSDT
INITIAL_CAPITAL=1000.0
MAX_DAILY_LOSS_PCT=5.0
MAX_POSITION_VALUE_PCT=80.0
EMERGENCY_STOP=false
UPDATE_INTERVAL=5
```

**Generate a secure SECRET_KEY:**
```python
# Run this in Python on the Pi:
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Save and exit nano (`Ctrl+X`, then `Y`, then Enter).

---

### Phase 6: Verify Installation (On Raspberry Pi)

```bash
# Check that all dependencies are installed
pip list | grep -E "flask|pydantic|pandas|numpy"

# Test import of main module
python3 -c "from src.main import app; print('Import successful')"
```

---

### Phase 7: Run the Bot (On Raspberry Pi)

```bash
# Ensure virtual environment is still activated
source venv/bin/activate

# Start the Flask application
python src/main.py
```

The bot will start and the web interface will be accessible at:
- **URL**: `http://192.168.1.112:8000`
- **Access from**: Any browser on your local network (Windows, Mac, phone, etc.)

---

### Phase 8: Running as Background Service (Optional)

For headless operation or to keep the bot running after SSH disconnect:

```bash
# Create a systemd service file
sudo nano /etc/systemd/system/bitbot.service
```

**Add this content:**
```ini
[Unit]
Description=BitbotV7 Trading Bot
After=network.target

[Service]
Type=simple
User=robbiegrant
WorkingDirectory=/home/robbiegrant/BitbotV7
Environment="PATH=/home/robbiegrant/BitbotV7/venv/bin"
ExecStart=/home/robbiegrant/BitbotV7/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable bitbot.service
sudo systemctl start bitbot.service

# Check status
sudo systemctl status bitbot.service

# View logs
journalctl -u bitbot.service -f
```

---

## Iterative Development Workflow

### Making Code Changes
1. **Edit files on Windows** in your local VS Code at `C:\Projects\BitbotV7`
2. **Transfer changes to Pi:**
   ```powershell
   # Copy specific changed files
   scp src/main.py robbiegrant@192.168.1.112:~/BitbotV7/src/
   
   # Or copy entire project (overwrite existing)
   scp -r C:\Projects\BitbotV7\* robbiegrant@192.168.1.112:~/BitbotV7/
   ```
3. **Restart the bot** on Pi:
   ```bash
   # If running directly:
   Ctrl+C  # Stop current process
   python src/main.py  # Restart
   
   # Or if using systemd service:
   sudo systemctl restart bitbot.service
   ```

### Alternative: Git-Based Workflow
For more robust version control and easier updates:

```bash
# On Raspberry Pi (first time setup)
cd ~/BitbotV7
git init
git add .
git commit -m "Initial commit"

# Add your Windows machine as a remote (or use GitHub/GitLab)
# Then push/pull changes between machines
```

---

## Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| `ssh: connect to host 192.168.1.112 port 22: Connection refused` | SSH not enabled on Pi, or wrong IP address |
| `Permission denied (publickey)` | Wrong username/password, check credentials |
| `ModuleNotFoundError: No module named 'flask'` | Dependencies not installed, run `pip install -r requirements.txt` |
| `Address already in use` | Port 8000 is occupied, change port in main.py or stop conflicting process |
| `ImportError: libffi.so.7: cannot open shared object file` | Install missing library: `sudo apt install libffi-dev` |

### Checking Pi Network Configuration
```bash
# Find Pi's IP address
hostname -I

# Or use nmap from Windows to discover devices on network
nmap -sn 192.168.1.0/24
```

---

## Success Criteria

- [ ] SSH connection successful with provided credentials
- [ ] System packages updated and dependencies installed
- [ ] Project files transferred to Pi without errors
- [ ] Python virtual environment created and activated
- [ ] All production dependencies installed successfully
- [ ] `.env` file configured with valid API keys
- [ ] `python src/main.py` starts without import errors
- [ ] Web interface accessible at `http://192.168.1.112:8000`
- [ ] Bot status page shows correct mode and style settings

---

## Next Steps After Installation

1. **Test the bot** in testnet mode with Binance Testnet API keys
2. **Monitor logs** for any errors or warnings
3. **Adjust trading parameters** based on performance
4. **Set up automated backups** of trade data and configuration
5. **Consider adding monitoring tools** (htop, nethogs) for resource usage
6. **Plan for production deployment** when ready to switch from testnet to live mode
