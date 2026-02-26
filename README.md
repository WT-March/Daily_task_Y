# Pilotage de Survie - Telegram Bot Setup

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 SERVER (VPS - 24/7)                     │
│  ┌─────────────────┐      ┌─────────────────────────┐   │
│  │  Python Bot     │◄────►│  PostgreSQL Database    │   │
│  │  telegram_bot/  │      │                         │   │
│  └─────────────────┘      └─────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                                       ▲
                                       │ sync
                                       ▼
                            ┌─────────────────┐
                            │  Rust TUI App   │
                            │  (your laptop)  │
                            └─────────────────┘
```

## Step 1: Get a Server

### Recommended Options:

| Provider | Price | Notes |
|----------|-------|-------|
| [Hetzner](https://www.hetzner.com/cloud) | ~4€/month | Best value, EU servers |
| [DigitalOcean](https://www.digitalocean.com/) | $6/month | Easy setup |
| [Railway.app](https://railway.app/) | Free tier | Good for testing |
| [Render.com](https://render.com/) | Free tier | Auto-deploys |

### Minimum specs:
- 1 CPU, 1GB RAM
- Ubuntu 22.04 LTS

## Step 2: Server Setup

### Connect to your server:
```bash
ssh root@your-server-ip
```

### Install dependencies:
```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.11+
apt install -y python3 python3-pip python3-venv

# Install PostgreSQL
apt install -y postgresql postgresql-contrib
```

### Setup PostgreSQL:
```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE pilotage_survie;
CREATE USER pilotage WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE pilotage_survie TO pilotage;
\c pilotage_survie
GRANT ALL ON SCHEMA public TO pilotage;
\q
```

### Create the tables:
```bash
sudo -u postgres psql -d pilotage_survie -f schema.sql
```

## Step 3: Create Telegram Bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Choose a name: `Pilotage Survie Bot`
4. Choose a username: `pilotage_survie_bot` (must end in `bot`)
5. **Save the token** you receive

### Get your Chat ID:
1. Search for **@userinfobot** on Telegram
2. Send `/start`
3. **Save your Chat ID**

## Step 4: Deploy the Bot

### Upload files to server:
```bash
# From your local machine
scp -r telegram_bot/* root@your-server-ip:/opt/pilotage-bot/
```

### Setup on server:
```bash
cd /opt/pilotage-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
nano .env
```

### Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id
DATABASE_URL=postgresql://pilotage:your_secure_password@localhost:5432/pilotage_survie
TIMEZONE=Europe/Paris
```

### Test the bot:
```bash
python bot.py
```

Send `/start` to your bot on Telegram. If it responds, it works!

## Step 5: Run as Service (systemd)

Create service file:
```bash
nano /etc/systemd/system/pilotage-bot.service
```

Content:
```ini
[Unit]
Description=Pilotage Survie Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pilotage-bot
ExecStart=/opt/pilotage-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
systemctl daemon-reload
systemctl enable pilotage-bot
systemctl start pilotage-bot

# Check status
systemctl status pilotage-bot

# View logs
journalctl -u pilotage-bot -f
```

## Step 6: Configure Rust App

Create `.env` file in your Rust app folder:
```bash
# C:\Users\...\Pilotage de Survie & Récupération\.env
DATABASE_URL=postgresql://pilotage:your_secure_password@your-server-ip:5432/pilotage_survie
```

### Allow remote PostgreSQL connections:

On server, edit PostgreSQL config:
```bash
nano /etc/postgresql/14/main/postgresql.conf
# Change: listen_addresses = '*'

nano /etc/postgresql/14/main/pg_hba.conf
# Add: host all all 0.0.0.0/0 md5

systemctl restart postgresql
```

### Test sync:
```bash
cargo run -- --sync
```

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/list` | Show today's tasks |
| `/add <title>` | Add a new task |
| `/done <id>` | Mark task as done |
| `/undone <id>` | Mark task as not done |
| `/delete <id>` | Delete a task |
| `/stats` | Show today's statistics |
| `/init` | Create default tasks |
| `/note <text>` | Add/update daily note |

## Security Notes

1. **Never commit `.env` files** to git
2. Use a **strong database password**
3. Consider using **SSH tunnel** instead of exposing PostgreSQL
4. Set up **UFW firewall** on your server

```bash
ufw allow 22    # SSH
ufw allow 5432  # PostgreSQL (only if needed)
ufw enable
```

## Troubleshooting

### Bot not responding:
```bash
journalctl -u pilotage-bot -n 50
```

### Database connection failed:
```bash
# Test locally
psql -U pilotage -d pilotage_survie -h localhost

# Test from laptop
psql -U pilotage -d pilotage_survie -h your-server-ip
```

### 21:00 reminder not sending:
- Check timezone in `.env`
- Check bot logs: `journalctl -u pilotage-bot -f`
