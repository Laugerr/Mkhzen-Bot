# 👁️ L'Mkhzen-Bot

L'Mkhzen is a structured Discord bot built for Medina Hub. It is designed as an authority system inspired by governance, hierarchy, and order, with a minimal and disciplined identity rather than a casual community-bot style.

## ⚙️ Features

- Modular `discord.py` architecture with auto-loaded cogs
- Slash-command support with Discord autocomplete and command hints
- Environment-based configuration with `python-dotenv`
- General utility commands for health checks and identity
- Moderation commands for warnings, warning removal, timed exile, exile history, pardon, and server logging
- Authority commands for rank inspection, hierarchy display, user audits, and channel-based announcements
- Shared configuration module for role names, hierarchy rules, and channel names
- Persistent JSON storage for moderation records

## 🏗️ Project Structure

```text
mkhzen-bot/
|-- bot.py
|-- cogs/
|   |-- __init__.py
|   |-- authority.py
|   |-- general.py
|   `-- moderation.py
|-- data/
|   |-- exiles.json
|   `-- warnings.json
|-- utils/
|   |-- __init__.py
|   |-- authority.py
|   |-- channels.py
|   |-- config.py
|   `-- storage.py
|-- .env
|-- .gitignore
|-- requirements.txt
`-- README.md
```

## 🧾 Commands

### 🛰️ General

- `/ping` shows bot latency
- `/about` describes the L'Mkhzen system
- `/status` shows the caller's visible server roles

### 🛡️ Moderation

- `/warn` issues a formal warning
- `/warnings` shows the latest recorded warnings for a member
- `/unwarn` removes one warning case from a member
- `/clearwarnings` removes all warnings for a member
- `/exile` assigns the `Quarantine` role for a timed exile
- `/exiles` shows exile history for a member
- `/timeleft` shows the remaining exile duration
- `/pardon` removes the `Quarantine` role

### 👑 Authority

- `/rank` shows a member's hierarchy level
- `/hierarchy` displays the full authority ladder
- `/audit` shows a member's rank, warning count, exile status, and roles
- `/announce` sends a styled authority announcement to `📢┃announcements`

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

4. Optional for faster local slash-command sync, add your server ID:

```env
DISCORD_GUILD_ID=your_medina_hub_server_id_here
```

5. In the Discord Developer Portal:
- enable `MESSAGE CONTENT INTENT`
- enable `SERVER MEMBERS INTENT`

6. Invite the bot to your server with these permissions:
- View Channels
- Send Messages
- Read Message History
- Embed Links
- Manage Roles

7. Start the bot:

```bash
python bot.py
```

## 🏷️ Role Configuration

Role names are centralized in `utils/config.py`. Update them there to match your Discord server exactly.

Channel names are also defined in `utils/config.py`, including:
- `📂┃server-logs`
- `📂┃activity-logs`
- `📢┃announcements`
- `🛡️┃staff-chat`
- `🤖bot-test`

Moderation records are stored in:
- `data/warnings.json`
- `data/exiles.json`

Default authority roles:

- `👑 Sultan 👑`
- `🕌 Wali 🕌`
- `🌟 Qaïd 🌟`
- `🛡️ Sheikh 🛡️`
- `🗡️ M'qaddem 🗡️`
- `🪔 F’qihs 🪔`
- `🏘️ Ahl Al-Medina 🏘️`
- `📖 Talebs 📖`
- `🐪 Nomads 🐪`
- `⛺ Travler ⛺`
- `Quarantine`

## 🗺️ Roadmap

- Output and embed design refinement
- Slash command permission refinement
- Database-backed authority records
