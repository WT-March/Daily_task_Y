# Pilotage de Survie - Telegram Bot Setup

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              SERVER (VPS + Coolify)                     │
│  ┌─────────────────┐      ┌─────────────────────────┐   │
│  │  Python Bot     │◄────►│  PostgreSQL Database    │   │
│  │  (Docker)       │      │  (Coolify service)      │   │
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

## Prerequisites

- A VPS with [Coolify](https://coolify.io) installed
- A Telegram account

---

## Step 1: Create Telegram Bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Choose a name: `Pilotage Survie Bot`
4. Choose a username: `pilotage_survie_bot` (must end in `bot`)
5. **Save the token** you receive

### Get your Chat ID:
1. Search for **@userinfobot** on Telegram
2. Send `/start`
3. **Save your Chat ID**

---

## Step 2: Setup PostgreSQL in Coolify

1. Go to your Coolify dashboard
2. Click **+ New Resource** → **Database** → **PostgreSQL**
3. Configure:
   - Name: `pilotage-db`
   - Database: `pilotage_survie`
   - Username: `pilotage`
   - Password: (generate a strong one)
4. Click **Deploy**
5. Once running, copy the **Internal URL** (looks like `postgresql://pilotage:xxx@pilotage-db:5432/pilotage_survie`)

### Initialize the database:

Connect to your PostgreSQL container and run `schema.sql`:

```bash
# In Coolify, open the database terminal or use:
psql -U pilotage -d pilotage_survie

# Then paste the contents of schema.sql
```

Or upload `schema.sql` and run:
```bash
psql -U pilotage -d pilotage_survie -f schema.sql
```

---

## Step 3: Deploy Bot with Coolify

### Option A: Deploy from Git Repository

1. Push `telegram_bot/` to a Git repo (GitHub, GitLab, etc.)
2. In Coolify: **+ New Resource** → **Application** → **Docker**
3. Connect your Git repository
4. Set the build context to `telegram_bot/` (or root if separate repo)
5. Add environment variables (see below)
6. Deploy

### Option B: Deploy with Docker Compose

1. In Coolify: **+ New Resource** → **Docker Compose**
2. Paste this configuration:

```yaml
services:
  pilotage-bot:
    build: .
    restart: always
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
      - DATABASE_URL=${DATABASE_URL}
      - TIMEZONE=${TIMEZONE}
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    restart: always
    environment:
      - POSTGRES_DB=pilotage_survie
      - POSTGRES_USER=pilotage
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./schema.sql:/docker-entrypoint-initdb.d/schema.sql

volumes:
  postgres_data:
```

### Environment Variables

In Coolify, add these environment variables:

| Variable | Value |
|----------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID |
| `DATABASE_URL` | `postgresql://pilotage:PASSWORD@pilotage-db:5432/pilotage_survie` |
| `TIMEZONE` | `Europe/Paris` |

---

## Step 4: Configure Rust App (Your Laptop)

Create `.env` file in your Rust app folder:

```env
DATABASE_URL=postgresql://pilotage:your_password@your-server-ip:5432/pilotage_survie
```

### Enable External PostgreSQL Access

In Coolify, for your PostgreSQL service:

1. Go to **Settings** → **Network**
2. Enable **Publicly Accessible** or add a port mapping (5432)
3. Or use Coolify's **Proxy** feature to expose the database

**Alternatively, use SSH tunnel (more secure):**
```bash
ssh -L 5432:localhost:5432 user@your-server-ip
```

Then your local `.env`:
```env
DATABASE_URL=postgresql://pilotage:your_password@localhost:5432/pilotage_survie
```

### Test sync:
```bash
cargo run -- --sync
```

---

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

---

## Coolify Tips

### View Logs
- Go to your application → **Logs** tab
- Or click **Terminal** to access the container

### Restart Bot
- Click **Restart** in the application dashboard

### Update Bot
- Push changes to Git → Coolify auto-deploys (if webhook configured)
- Or click **Redeploy** manually

### Monitor Health
- Coolify shows container status and resource usage
- Set up notifications in Coolify settings

---

## Troubleshooting

### Bot not responding:
1. Check Coolify logs for errors
2. Verify environment variables are set correctly
3. Test database connection from bot container

### Database connection failed:
```bash
# In bot container terminal:
python -c "from database import get_connection; print(get_connection())"
```

### 21:00 reminder not sending:
- Check `TIMEZONE` environment variable
- Verify bot is running (check Coolify dashboard)

---

## Security Notes

1. **Never commit `.env` files** to git
2. Use Coolify's **Secrets** for sensitive values
3. Keep PostgreSQL internal (not publicly exposed) if possible
4. Use SSH tunnel for laptop connection instead of exposing port 5432
