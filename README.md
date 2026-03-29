# 👁️ Mkhzen-Bot

Mkhzen is a structured Discord bot built for Medina Hub. It is designed as an authority system inspired by governance, hierarchy, and order, with a minimal and disciplined identity rather than a casual community-bot style.

## ⚙️ Features

- Modular `discord.py` architecture with auto-loaded cogs
- Environment-based configuration with `python-dotenv`
- General utility commands for health checks and identity
- Moderation commands for warnings, exile, and pardon flows
- Authority commands for rank inspection and formal announcements
- Shared configuration module for role names and hierarchy rules

## 🏗️ Project Structure

```text
mkhzen-bot/
|-- bot.py
|-- cogs/
|   |-- __init__.py
|   |-- authority.py
|   |-- general.py
|   `-- moderation.py
|-- utils/
|   |-- __init__.py
|   `-- config.py
|-- .env
|-- .gitignore
|-- requirements.txt
`-- README.md
```

## 🧾 Commands

### 🛰️ General

- `!ping` shows bot latency
- `!about` describes the Mkhzen system
- `!status` shows the caller's visible server roles

### 🛡️ Moderation

- `!warn @user [reason]` issues a formal warning
- `!exile @user [reason]` assigns the `Quarantine` role
- `!pardon @user` removes the `Quarantine` role

### 👑 Authority

- `!rank @user` shows a member's hierarchy level
- `!announce <message>` sends a styled authority announcement

## 🚀 Setup

1. Create and activate a Python 3 virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Add your bot token to `.env`:

```env
DISCORD_TOKEN=your_token_here
```

4. In the Discord Developer Portal:
- enable `MESSAGE CONTENT INTENT`
- enable `SERVER MEMBERS INTENT`

5. Invite the bot to your server with these permissions:
- View Channels
- Send Messages
- Read Message History
- Embed Links
- Manage Roles

6. Start the bot:

```bash
python bot.py
```

## 🏷️ Role Configuration

Role names are centralized in `utils/config.py`. Update them there to match your Discord server exactly.

Default authority roles:

- `👑 Sultan 👑`
- `🏰 Wali 🏰`
- `☀️ Qaid ☀️`
- `🛡️ Sheikh 🛡️`
- `🗡️ M'qaddem 🗡️`
- `🪔 F'qihs 🪔`
- `🏘️ Ahl Al-Medina 🏘️`
- `📖 Talebs 📖`
- `🐪 Nomads 🐪`
- `⛺ Traveler ⛺`
- `Quarantine`

## 🗺️ Roadmap

- Persistent warning storage
- Case logs and moderation history
- Slash command support
- Permission tiers by rank
- Database-backed authority records
- Versioned architecture for `v2` and `v3`
