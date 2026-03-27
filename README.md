# AutoPixel

**Pixel 10 Pro Google One Offer Automation Bot (Telegram)**

AutoPixel is a production-ready Telegram automation bot that simulates a
Pixel 10 Pro (Android 16), signs in with a user-provided Google account,
and checks whether the account is eligible for the
**12-month Gemini Pro promotional offer** from Google One.

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-1f6feb)
![Runtime](https://img.shields.io/badge/runtime-Python%203.10%2B-3776AB)
![Container](https://img.shields.io/badge/container-Docker-2496ED)
![Architecture](https://img.shields.io/badge/architecture-modular-2ea043)

### Highlights

- Modular architecture (core, handlers, services)
- Secure in-memory credential handling with wipe logic
- Cross-platform execution (Windows, Linux, macOS)
- Docker-first deployment for predictable operations

### Release Notes

- See [CHANGELOG.md](CHANGELOG.md) for version history and release details.

## At a Glance

| Category | Details |
|---|---|
| Primary interface | Telegram bot commands |
| Main automation target | Google One offer flow |
| Device simulation | Pixel 10 Pro (Android 16) |
| Authentication support | Gmail + Google Workspace |
| 2FA support | Authenticator/TOTP flow |
| Deployment options | Local Python or Docker Compose |

---

## Project Structure

```
autopixel/
├── main.py               # Telegram bot entry point
├── core/
│   ├── __init__.py
│   ├── runtime_state.py      # Shared rate-limit + concurrency state
│   └── session_manager.py    # Session lifecycle and secure wipe helpers
├── handlers/
│   ├── __init__.py
│   ├── bot_handlers.py        # Compatibility facade exports
│   ├── auth_handlers.py       # /start /login /logout flows
│   ├── offer_handlers.py      # /check_offer + 2FA flows
│   ├── session_handlers.py    # /status /get_link + cleanup job
│   └── states.py              # Conversation state constants
├── services/
│   ├── __init__.py
│   ├── device_simulator.py   # Public device simulator facade
│   ├── device_simulator_core/
│   │   ├── __init__.py
│   │   ├── constants.py      # Pixel hardware/emulation constants
│   │   ├── generators.py     # IMEI/Android ID/fingerprint helpers
│   │   ├── profile.py        # DeviceProfile model + spoof payloads
│   │   └── factory.py        # create_device_profile factory
│   ├── google_automation.py  # Public automation facade
│   └── google_automation_core/
│       ├── __init__.py
│       ├── api.py            # Public callable service functions
│       ├── errors.py         # Domain exceptions
│       ├── driver_factory.py # WebDriver + emulation setup
│       ├── login_flow.py     # Google login + TOTP flow
│       └── offer_scanner.py  # Offer detection and link extraction
├── config.py             # Configuration and constants
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Docker Compose orchestration
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## Features

| Feature | Details |
|---|---|
| Device simulation | Pixel 10 Pro profile with unique IMEI, Android ID, and user-agent per session |
| Telegram UX | Command-based flow with modern reply keyboards and quick actions |
| Authentication | Selenium-powered Google sign-in (Gmail + Workspace) |
| Offer detection | Multi-attempt Google One scanning with retry strategy |
| Session lifecycle | In-memory per-user sessions with secure credential wiping |
| Safety controls | Cooldown, concurrency limit, and structured error handling |

---

## Supported Regions (Pixel 10 Series Offer)

This regional matrix applies to all three models:
**Pixel 10 Pro**, **Pixel 10 Pro XL**, and **Pixel 10 Pro Fold**.

| Coverage Metric | Value |
|---|---|
| Supported devices | Pixel 10 Pro / Pixel 10 Pro XL / Pixel 10 Pro Fold |
| Total supported regions | 33 |
| Regional status | ✅ Officially supported |

| Americas | Europe | APAC |
|---|---|---|
| Canada<br>Mexico<br>United States | Austria<br>Belgium<br>Czech Republic<br>Denmark<br>Estonia<br>Finland<br>France<br>Germany<br>Hungary<br>Ireland<br>Italy<br>Latvia<br>Lithuania<br>Netherlands<br>Norway<br>Poland<br>Portugal<br>Romania<br>Slovakia<br>Slovenia<br>Spain<br>Sweden<br>Switzerland<br>United Kingdom | Australia<br>India<br>Japan<br>Malaysia<br>Singapore<br>Taiwan |

> Note: Offer availability can still vary by account eligibility, subscription history, and Google policy checks.

---

## Eligibility Checklist

Before running `/check_offer`, validate this checklist to improve success rate:

| Check | Why it matters | Recommended action |
|---|---|---|
| Region eligibility | Offer is region-limited | Confirm account and IP region are in supported regions |
| Account offer history | Prior claim can block new claim | Use an account that has not redeemed the same promo |
| Active subscriptions | Existing Gemini/Google One plans may disqualify | Review and verify subscription status in Google account |
| Family group state | Family eligibility can be consumed by another member | Check Google family group plan/benefit state |
| 2FA method | Unsupported challenges interrupt automation | Prefer TOTP/Auth app for automated flow |
| Login security posture | New or high-risk sessions trigger challenges | Use a stable device/IP and avoid rapid account switching |

---

## Troubleshooting by Symptom

| Symptom | Likely cause | Next step |
|---|---|---|
| `No credentials found` | Session not initialized | Run `/login` and submit account details again |
| `Automation Error: Chromium is not installed` | Browser path not available | Install Chrome/Chromium or set `CHROME_BIN` |
| `Code rejected` during 2FA | Invalid/expired TOTP code | Re-check TOTP secret and sync system time |
| `No Gemini Pro offer found after 3 attempts` | Account/region not eligible or offer already consumed | Verify eligibility checklist and test another account |
| Repeated challenge prompts | Account risk controls or unusual login signals | Keep region/IP stable and reduce aggressive retries |
| Bot starts but does not respond | Token/webhook/session issue | Verify `TELEGRAM_BOT_TOKEN`, restart bot, review logs |

> Tip: If manual browser check also shows no offer for the same account, bot automation will not be able to force eligibility.

---

## Quick Start (Local)

```bash
# 1) Create virtual environment
python -m venv .venv

# 2) Activate environment
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

# 3) Install dependencies
pip install -r requirements.txt

# 4) Configure environment
cp .env.example .env
# Set TELEGRAM_BOT_TOKEN in .env

# 5) Run bot
python main.py
```

---

## Deployment (Ubuntu + Docker)

### Prerequisites

- Ubuntu 24.04 64-bit server
- Docker and Docker Compose installed

### 1. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect
```

### 2. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` and follow the prompts.
3. Copy the API token you receive (looks like `123456:ABC-DEF…`).

### 3. Clone and configure

```bash
git clone https://github.com/imnoob59/autopixel.git autopixel
cd autopixel

# Create environment file
cp .env.example .env
nano .env
# Set TELEGRAM_BOT_TOKEN=<your token from BotFather>
```

### 4. Build and run

```bash
docker compose up -d --build
```

### 5. Management commands

```bash
# Stop bot
docker compose stop

# Stop and remove containers
docker compose down

# Restart
docker compose restart

# Rebuild after code updates
docker compose up -d --build

# View live logs (console)
docker compose logs -f

# View log file
cat logs/bot.log

# View last 100 log lines
tail -n 100 logs/bot.log

# View container status
docker compose ps

# Check the main container directly
docker ps --filter "name=autpixel"
```

> **Note**: The container uses the `restart: on-failure:3` policy and will
> auto-restart only on failure (up to 3 times).
> Manual `docker compose stop` or `docker compose down` will not trigger restart.

---

## Usage

| Command | Description |
|---|---|
| `/start` | Show welcome message and command list |
| `/login` | Enter Gmail email and password (two-step conversation) |
| `/check_offer` | Simulate device, log in, and search for the Gemini Pro offer |
| `/get_link` | Retrieve the last captured offer link |
| `/status` | View current session info and device profile |
| `/logout` | Securely clear credentials and session data |

### Typical flow

```
You: /start
Bot: Welcome…

You: /login
Bot: Please enter your Gmail address:

You: user@gmail.com
Bot: Email received. Now enter your password:

You: ••••••••
Bot: ✅ Credentials saved. New Pixel 10 Pro device profile created…

You: /check_offer
Bot: ⏳ Launching device simulator…
Bot: 🎉 Gemini Pro Offer Found! 🔗 https://one.google.com/…
```

---

## Technical Notes

- **Headless Chrome** is used via Selenium with mobile emulation matching
  the Pixel 10 Pro screen dimensions (390 × 844, pixel ratio 3.0).
- A new **IMEI**, **Android ID**, and **Chrome version patch** are generated
  for every session using the `device_simulator.py` module.
- Credentials are stored as **`bytearray`** objects for secure in-place
  memory erasure. Passwords are wiped after use and never written to disk.
- **Rate limiting**: 5-minute cooldown per user between `/check_offer` calls.
- **Concurrency control**: Maximum 3 simultaneous Chrome instances.
- Session **TTL** of 30 minutes with automatic cleanup.

---

## Requirements

- Docker (recommended) or Python 3.10+ with Chromium and chromedriver
- A Telegram Bot token from @BotFather

---

## Disclaimer

This project is provided for educational and personal use only.
Automating Google account access may violate Google's Terms of Service.
Use responsibly and only with accounts you own.
