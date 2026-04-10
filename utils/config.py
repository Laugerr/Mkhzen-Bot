SERVER_NAME = "Medina Hub"

SULTAN_ROLE = "\U0001f451 Sultan \U0001f451"
WALI_ROLE = "\U0001f54c Wali \U0001f54c"
QAID_ROLE = "\U0001f31f Qa\u00efd \U0001f31f"
SHEIKH_ROLE = "\U0001f6e1\ufe0f Sheikh \U0001f6e1\ufe0f"
MQADDEM_ROLE = "\U0001f5e1\ufe0f M'qaddem \U0001f5e1\ufe0f"
FQIHS_ROLE = "\U0001fa94 F\u2019qihs \U0001fa94"
AHL_AL_MEDINA_ROLE = "\U0001f3d8\ufe0f Ahl Al-Medina \U0001f3d8\ufe0f"
TALEBS_ROLE = "\U0001f4d6 Talebs \U0001f4d6"
NOMADS_ROLE = "\U0001f42a Nomads \U0001f42a"
TRAVELER_ROLE = "\u26fa Travler \u26fa"
QUARANTINE_ROLE = "Quarantine"
SERVER_LOGS_CHANNEL = "\U0001f4c2\u2503server-logs"
ACTIVITY_LOGS_CHANNEL = "\U0001f4c2\u2503activity-logs"
ANNOUNCEMENTS_CHANNEL = "\U0001f4e2\u2503announcements"
STAFF_CHAT_CHANNEL = "\U0001f6e1\ufe0f\u2503staff-chat"
BOT_TEST_CHANNEL = "\U0001f916bot-test"
WELCOME_CHANNEL = "\U0001f44b\u2503welcome"
VERIFY_CHANNEL = "\u2705\u2503verify-here"
RULES_CHANNEL = "\U0001f4dc\u2503rules"
VERIFIED_ROLE = NOMADS_ROLE
UNVERIFIED_ROLE = TRAVELER_ROLE
VERIFY_REACTION_EMOJI = "\u2705"
WELCOME_BANNER_PATH = "assets/welcome-banner.png"
WELCOME_BANNER_URL = ""
WELCOME_AVATAR_CENTER_X = 760
WELCOME_AVATAR_CENTER_Y = 158
WELCOME_AVATAR_SIZE = 190

AUTHORITY_HIERARCHY = [
    SULTAN_ROLE,
    WALI_ROLE,
    QAID_ROLE,
    SHEIKH_ROLE,
    MQADDEM_ROLE,
    FQIHS_ROLE,
    AHL_AL_MEDINA_ROLE,
    TALEBS_ROLE,
    NOMADS_ROLE,
    TRAVELER_ROLE,
]

ANNOUNCE_ALLOWED_ROLES = [
    SULTAN_ROLE,
    WALI_ROLE,
    QAID_ROLE,
]

MODERATION_ALLOWED_ROLES = [
    SULTAN_ROLE,
    WALI_ROLE,
    QAID_ROLE,
    SHEIKH_ROLE,
    MQADDEM_ROLE,
]

ANNOUNCE_EMBED_COLOR = 0x8B1E1E
MODERATION_EMBED_COLOR = 0xC0392B
STATUS_EMBED_COLOR = 0x0F766E
GOVERNANCE_EMBED_COLOR = 0x2C3E50
PRESTIGE_EMBED_COLOR = 0x8E44AD

# ─── AUTO-ROLE ────────────────────────────────────────────────────────────────

JOIN_AUTO_ROLE = TRAVELER_ROLE

# ─── WARNING THRESHOLD → AUTO-EXILE ──────────────────────────────────────────

WARNING_EXILE_THRESHOLD = 3        # warnings before automatic exile is triggered
WARNING_EXILE_DURATION = "1h"      # duration string for the auto-exile

# ─── INTEREST ROLES (self-assignable after verification) ─────────────────────
# Add role names that exist on your server. Leave empty to disable /roles.

INTEREST_ROLES: list[str] = []

# ─── PRESTIGE SYSTEM ─────────────────────────────────────────────────────────

PRESTIGE_XP_PER_MESSAGE = 2        # base XP awarded per eligible message
PRESTIGE_DAILY_CAP = 100           # max XP earnable from messages per day
PRESTIGE_XP_COOLDOWN = 60          # seconds between XP-eligible messages per member
PRESTIGE_DECAY_INACTIVE_DAYS = 30  # days of inactivity before decay begins
PRESTIGE_DECAY_AMOUNT = 5          # prestige lost per decay cycle
PRESTIGE_ENFORCE_MINIMUM = False   # if True, /promote is blocked below minimum

PRESTIGE_PROMOTION_MINIMUMS: dict[str, int] = {
    # role_name: minimum prestige required to be eligible for promotion to that role
    # Populated as advisory defaults — adjust to match your server's pace
    NOMADS_ROLE:       0,
    AHL_AL_MEDINA_ROLE: 100,
    TALEBS_ROLE:       300,
    FQIHS_ROLE:        600,
    MQADDEM_ROLE:      1000,
    SHEIKH_ROLE:       1500,
    QAID_ROLE:         2000,
    WALI_ROLE:         3000,
    SULTAN_ROLE:       5000,
}
