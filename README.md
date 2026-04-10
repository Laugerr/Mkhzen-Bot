# 👁️ L'Mkhzen-Bot

L'Mkhzen is the authority system of **Medina Hub** — a structured Discord bot built around governance, hierarchy, and server order. Disciplined by design, not casual.

---

## ✨ Features

- 🧩 Modular `discord.py` architecture with auto-loaded cogs
- ⚡ Slash-command support with Discord autocomplete
- 🔐 Environment-based configuration with `python-dotenv`
- 🩺 Startup validation for required roles, channels, and welcome assets
- 🛡️ Full moderation suite: warnings, exile, pardon, ban, expel, staff notes
- ⚠️ Auto-exile triggered when a member reaches the warning threshold
- 👑 Authority system: rank, hierarchy, audit, promote, demote, decrees, and stats
- 🗳️ Council votes with live Aye/Nay buttons and auto-close
- 📨 Member appeal system with staff review and DM resolution
- 🎭 Interest role picker via select menu (`/roles`)
- 🖼️ Welcome banner with member avatar composited at join
- 📩 Welcome DM sent to every new member with onboarding instructions
- 🚪 Auto-assigns the Traveler role on join
- ✅ Reaction-based verification gate with role transition
- 📋 Paginated output — navigate all history lists with ◀ Prev / Next ▶ buttons
- 🆔 Stable case IDs — removed warnings never cause renumbering
- ⭐ **Prestige system** — passive XP from messages + staff honour grants + daily decay
- 🏆 Live leaderboard showing top members by Prestige tier
- 📡 Full event logging: joins, leaves, bans, message edits/deletes, role changes
- ⏱️ Rate limiting on all commands
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
│   ├── authority.py       👑 Rank, hierarchy, audit, promote, demote, stats
│   ├── general.py         🛰️ Ping, about, status
│   ├── governance.py      🏛️ Decrees, votes, appeals, interest roles
│   ├── logging.py         📡 Event logging (joins, messages, roles, bans)
│   ├── moderation.py      🛡️ Warnings, exile, pardon, ban, expel, notes
│   ├── onboarding.py      🚪 Welcome, verify, rules, auto-role
│   └── prestige.py        ⭐ XP system, leaderboard, honour
├── data/
│   ├── appeals.json
│   ├── decrees.json
│   ├── exiles.json
│   ├── notes.json
│   ├── prestige.json
│   ├── verification.json
│   ├── votes.json
│   └── warnings.json
├── utils/
│   ├── __init__.py
│   ├── authority.py       Rank resolution helpers
│   ├── channels.py        Channel lookup utilities
│   ├── config.py          Centralized configuration
│   ├── decrees.py         Decree, appeal, and vote storage
│   ├── notes.py           Staff notes storage
│   ├── paginator.py       Discord UI paginator
│   ├── prestige.py        XP and prestige storage + decay
│   ├── roles.py           Role lookup utility
│   ├── storage.py         Warnings and exile persistence
│   ├── time_utils.py      Shared duration parsing/formatting
│   ├── validation.py      Startup guild validation
│   ├── verification.py    Verification registry
│   └── welcome_card.py    Avatar banner compositing
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
| `/ping` | 🏓 Bot latency with signal quality indicator |
| `/about` | 👁️ Describe the L'Mkhzen system |
| `/status` | 🪪 Your current rank and visible roles |

### 🛡️ Moderation

| Command | Description |
|---|---|
| `/warn` | ⚠️ Issue a formal warning (auto-exile triggers at threshold) |
| `/warnings` | 📋 Browse a member's warning history (paginated) |
| `/unwarn` | ✅ Remove a specific warning case by stable ID |
| `/clearwarnings` | 🧹 Purge all warnings for a member |
| `/exile` | ⛓️ Assign timed quarantine (`10m`, `2h`, `1d`) |
| `/exiles` | 📜 Browse a member's exile history (paginated) |
| `/timeleft` | ⏳ Show remaining time on an active exile |
| `/pardon` | 🕊️ Release a member from quarantine early |
| `/ban` | 🔨 Permanently ban a member (Sultan/Wali/Qaïd only) |
| `/expel` | 🚪 Kick a member with a logged record |
| `/note` | 📌 Add a private staff note on a member |
| `/notes` | 📌 View all staff notes on a member |
| `/delnote` | 🗑️ Delete a specific staff note |

### 👑 Authority

| Command | Description |
|---|---|
| `/rank` | 🏅 Show a member's hierarchy tier and badge |
| `/hierarchy` | 👑 Display the full authority ladder (paginated) |
| `/audit` | 🔍 Full dossier: rank, prestige, warnings, exile, roles |
| `/announce` | 📣 Send an official decree to the announcements channel |
| `/promote` | 📈 Promote a member one tier up the hierarchy |
| `/demote` | 📉 Demote a member one tier down (−50% Prestige penalty) |
| `/stats` | 📊 Server statistics: members, exiles, warnings, role breakdown |

### 🏛️ Governance

| Command | Description |
|---|---|
| `/decree` | 📜 Issue an official decree, archive it, and post to announcements |
| `/decrees` | 📚 Browse the full decree archive (paginated) |
| `/repeal` | 🚫 Repeal an active decree by ID |
| `/vote` | 🗳️ Open a council vote with live Aye/Nay buttons |
| `/appeal` | 📨 Submit a moderation appeal to staff |
| `/appeals` | 📋 List all open member appeals (staff only) |
| `/resolve` | ✅ Resolve an open appeal and notify the member |
| `/roles` | 🎭 Browse and self-assign interest roles |

### ⭐ Prestige

| Command | Description |
|---|---|
| `/prestige` | ⭐ View a member's Prestige score, tier, and daily progress bar |
| `/leaderboard` | 🏆 Top 10 members by accumulated Prestige |
| `/honour` | ✨ Grant or deduct Prestige from a member (senior staff only) |

### 🚪 Onboarding

| Command | Description |
|---|---|
| `/testwelcome` | 🖼️ Send a test welcome banner to yourself |
| `/setupverify` | ✅ Post the reaction verification gate |
| `/setuprules` | 📜 Post the Medina Code rules panel |

---

## ⭐ Prestige System

Members earn **Prestige** passively by chatting (capped per day) and through staff **Honour** grants. It serves as a visible signal of engagement — not automatic advancement.

| Source | Amount |
|---|---|
| 💬 Message (1 per minute) | +2 XP |
| 📅 Daily cap | 100 XP max |
| 🎖️ Staff `/honour` grant | Any amount |
| 📉 Inactivity decay (after 30 days) | −5 / cycle |
| ⬇️ Demotion penalty | −50% |

**Prestige Tiers:**

| Tier | Threshold |
|---|---|
| 🔘 Newcomer | 0+ |
| 🥉 Bronze | 50+ |
| 🥈 Silver | 200+ |
| 🥇 Gold | 500+ |
| 🏆 Platinum | 1,000+ |
| 💎 Diamond | 2,000+ |
| 🌟 Legendary | 5,000+ |

> Promotion minimums are advisory by default. Set `PRESTIGE_ENFORCE_MINIMUM = True` in `config.py` to make them a hard requirement for `/promote`.

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
DISCORD_GUILD_ID=your_server_id_here
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
- Kick Members
- Ban Members
- Add Reactions
- Attach Files

**7.** Start the bot:

```bash
python bot.py
```

**8.** Watch the terminal on startup — validation warnings will surface any missing roles, channels, or welcome assets.

---

## 🏷️ Configuration

All settings live in `utils/config.py`. Update them to match your server.

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
| `📂┃server-logs` | 🛡️ Moderation + role change logs |
| `📂┃activity-logs` | 📊 Join/leave, message edit/delete logs |
| `📢┃announcements` | 📣 Decree and announcement target |
| `🛡️┃staff-chat` | 🔐 Appeal notifications |
| `🤖bot-test` | 🧪 Bot testing |
| `👋┃welcome` | 🖼️ Welcome banner destination |
| `✅┃verify-here` | ✅ Verification gate |
| `📜┃rules` | 📜 Rules panel |

### ⚙️ Key Settings

| Setting | Default | Description |
|---|---|---|
| `JOIN_AUTO_ROLE` | Traveler | Role assigned to every new member |
| `WARNING_EXILE_THRESHOLD` | `3` | Warnings before auto-exile triggers |
| `WARNING_EXILE_DURATION` | `"1h"` | Duration of the auto-exile |
| `INTEREST_ROLES` | `[]` | Self-assignable roles for `/roles` — add role names here |
| `PRESTIGE_XP_PER_MESSAGE` | `2` | XP per eligible message |
| `PRESTIGE_DAILY_CAP` | `100` | Max message XP per day |
| `PRESTIGE_XP_COOLDOWN` | `60s` | Minimum gap between XP-eligible messages |
| `PRESTIGE_DECAY_INACTIVE_DAYS` | `30` | Days of inactivity before decay |
| `PRESTIGE_DECAY_AMOUNT` | `5` | Prestige lost per decay cycle |
| `PRESTIGE_ENFORCE_MINIMUM` | `False` | Block `/promote` below prestige minimum |

### 💾 Data Files

| File | Contents |
|---|---|
| `data/warnings.json` | ⚠️ Warning case records |
| `data/exiles.json` | ⛓️ Exile history and active exiles |
| `data/notes.json` | 📌 Private staff notes |
| `data/prestige.json` | ⭐ Member XP and Prestige scores |
| `data/decrees.json` | 📜 Official decree archive |
| `data/appeals.json` | 📨 Member appeal records |
| `data/votes.json` | 🗳️ Council vote records |
| `data/verification.json` | ✅ Verification gate registry |

---

## 🗺️ Roadmap

- 🗄️ Database-backed storage (SQLite or PostgreSQL)
- 🔁 Hot-reload config without bot restart
- 📊 Weekly activity digests
- 🛂 Voice channel activity XP
