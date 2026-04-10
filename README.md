# 👁️ L'Mkhzen-Bot

L'Mkhzen is the authority system of **Medina Hub** — a structured Discord bot built around governance, hierarchy, and server order. Disciplined by design, not casual.

---

## ✨ Features

- 🧩 Modular `discord.py` architecture with auto-loaded cogs
- ⚡ Slash-command support with Discord autocomplete
- 🔐 Environment-based configuration with `python-dotenv`
- 🩺 Startup validation for required roles, channels, and welcome assets
- 🛡️ Moderation system: warnings, timed exile, pardon, and persistent case history
- 👑 Authority system: rank inspection, hierarchy display, user audits, and decrees
- 🖼️ Welcome banner with member avatar composited at join
- ✅ Reaction-based verification gate with role transition
- 📋 Paginated output — navigate warning/exile history with ◀ Prev / Next ▶ buttons
- 🆔 Stable case IDs — removed warnings never cause ID renumbering
- ⏱️ Rate limiting on all commands to prevent abuse
- 📡 Global error handler for clean, styled error responses
- 🔊 Structured audit logging for every moderation action

---

## 🏗️ Project Structure

```text
mkhzen-bot/
├── assets/
│   └── welcome-banner.png
├── bot.py
├── cogs/
│   ├── __init__.py
│   ├── authority.py
│   ├── general.py
│   ├── moderation.py
│   └── onboarding.py
├── data/
│   ├── exiles.json
│   ├── verification.json
│   └── warnings.json
├── utils/
│   ├── __init__.py
│   ├── authority.py
│   ├── channels.py
│   ├── config.py
│   ├── paginator.py
│   ├── roles.py
│   ├── storage.py
│   ├── validation.py
│   ├── verification.py
│   └── welcome_card.py
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🧾 Commands

### 🛰️ General

| Command | Description |
|---|---|
| `/ping` | 🏓 Show bot latency with signal quality indicator |
| `/about` | 👁️ Describe the L'Mkhzen authority system |
| `/status` | 🪪 Show your current rank and visible server roles |

### 🛡️ Moderation

| Command | Description |
|---|---|
| `/warn` | ⚠️ Issue a formal warning with a persistent case ID |
| `/warnings` | 📋 Browse a member's full warning history (paginated) |
| `/unwarn` | ✅ Remove a specific warning case by ID |
| `/clearwarnings` | 🧹 Purge all warnings for a member |
| `/exile` | ⛓️ Assign timed quarantine (`10m`, `2h`, `1d`) |
| `/exiles` | 📜 Browse a member's full exile history (paginated) |
| `/timeleft` | ⏳ Show remaining time on an active exile |
| `/pardon` | 🕊️ Release a member from quarantine early |

### 👑 Authority

| Command | Description |
|---|---|
| `/rank` | 🏅 Show a member's hierarchy tier and badge |
| `/hierarchy` | 👑 Display the full authority ladder (paginated) |
| `/audit` | 🔍 Full dossier: rank, status, warnings, exile, roles |
| `/announce` | 📣 Send an official decree to the announcements channel |

### 🚪 Onboarding

| Command | Description |
|---|---|
| `/testwelcome` | 🖼️ Send a test welcome banner to yourself |
| `/setupverify` | ✅ Post the reaction verification gate |
| `/setuprules` | 📜 Post the Medina Code rules panel |

---

## 🚀 Setup

**1.** Create and activate a Python 3 virtual environment.

**2.** Install dependencies:

```bash
pip install -r requirements.txt
```

**3.** Add your bot token to `.env`:

```env
DISCORD_TOKEN=your_token_here
```

**4.** *(Optional)* For faster local slash-command sync, add your server ID:

```env
DISCORD_GUILD_ID=your_medina_hub_server_id_here
```

**5.** In the **Discord Developer Portal**, enable:
- `MESSAGE CONTENT INTENT`
- `SERVER MEMBERS INTENT`

**6.** Invite the bot with these permissions:
- View Channels
- Send Messages
- Read Message History
- Embed Links
- Manage Roles
- Add Reactions
- Attach Files

**7.** Start the bot:

```bash
python bot.py
```

**8.** Watch the terminal on startup — validation warnings will surface any missing roles, channels, or welcome assets.

---

## 🏷️ Configuration

All role names and channel names are centralized in `utils/config.py`. Update them there to match your Discord server exactly.

### 🎭 Default Authority Roles

| Rank | Role Name |
|---|---|
| 👑 1 | `👑 Sultan 👑` |
| 🥇 2 | `🕌 Wali 🕌` |
| 🥈 3 | `🌟 Qaïd 🌟` |
| 🥉 4 | `🛡️ Sheikh 🛡️` |
| 🏅 5 | `🗡️ M'qaddem 🗡️` |
| 🎖️ 6 | `🪔 F'qihs 🪔` |
| ⚜️ 7 | `🏘️ Ahl Al-Medina 🏘️` |
| 📜 8 | `📖 Talebs 📖` |
| 🌿 9 | `🐪 Nomads 🐪` |
| ⛺ 10 | `⛺ Travler ⛺` |
| 🔒 — | `Quarantine` |

### 📡 Default Channels

| Channel | Purpose |
|---|---|
| `📂┃server-logs` | 🛡️ Moderation log destination |
| `📂┃activity-logs` | 📊 Activity log destination |
| `📢┃announcements` | 📣 Authority announcement target |
| `🛡️┃staff-chat` | 🔐 Staff private channel |
| `🤖bot-test` | 🧪 Bot testing channel |
| `👋┃welcome` | 🖼️ Welcome banner destination |
| `✅┃verify-here` | ✅ Verification gate channel |
| `📜┃rules` | 📜 Rules panel channel |

### 🖼️ Welcome Banner Settings

| Setting | Key |
|---|---|
| Banner path | `WELCOME_BANNER_PATH` |
| Avatar center X | `WELCOME_AVATAR_CENTER_X` |
| Avatar center Y | `WELCOME_AVATAR_CENTER_Y` |
| Avatar size (px) | `WELCOME_AVATAR_SIZE` |
| Verified role | `VERIFIED_ROLE` |
| Unverified role | `UNVERIFIED_ROLE` |
| Reaction emoji | `VERIFY_REACTION_EMOJI` |

### 💾 Data Files

| File | Contents |
|---|---|
| `data/warnings.json` | ⚠️ Warning case records |
| `data/exiles.json` | ⛓️ Exile history and active exiles |
| `data/verification.json` | ✅ Verification gate registry |

---

## 🗺️ Roadmap

- 🗄️ Database-backed authority records
- 🔁 Hot-reload config without bot restart
- 📊 Activity tracking and member stats
- 🛂 Appeal system for exile reviews
