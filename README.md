# AutoPixel

**Pixel 10 Pro Google One Assistant**  
Created by **Nadif Rizky**

AutoPixel is a Telegram bot that simulates a Pixel 10 Pro session, signs in to a Google account, checks Google One / Gemini offer availability, and gives you a modern control panel for session, proxy, IP, and diagnostic tools.

## What This Bot Does

- Simulates a fresh Pixel 10 Pro device profile for each login session
- Supports Gmail and Google Workspace accounts
- Handles Google sign-in with TOTP / authenticator flow support
- Checks Google One pages for Gemini / AI Pro offer availability
- Supports proxy pool rotation and direct/local IP mode
- Shows public IP, region, ZIP, org, ISP, ASN, timezone, and other proxy identity details
- Saves screenshot + HTML debug artifacts when no offer is found
- Supports English and Indonesian UI
- Ships with a modern Telegram dashboard:
  - header media
  - 2-column grid buttons
  - `[·]` section cards
  - emoji-rich menu labels

## Main Commands

| Command | Function |
|---|---|
| `/start` | Open the Pixel Control Panel |
| `/login` | Save Google email + password and create a fresh device session |
| `/check_offer` | Start login automation and scan Google One for an offer |
| `/get_link` | Show the last captured offer link |
| `/status` | Show account, proxy, and device session info |
| `/proxy` | Show the active proxy and proxy pool status |
| `/ip` | Show public IP and geo/identity data |
| `/rotate_proxy` | Switch to another proxy from the pool |
| `/disable_proxy` | Force the session to use direct/local IP |
| `/lang_en` | Switch bot UI to English |
| `/lang_id` | Switch bot UI to Indonesian |
| `/langid` | Alias for `/lang_id` |
| `/logout` | Clear active session, credentials, and temporary browser state |
| `/cancel` | Cancel the current login / verification flow |

## Current UI

The bot now uses:

- a modern welcome card
- a local banner/header image on `/start`
- a 2-column inline control panel
- reply-keyboard navigation buttons
- branded text showing **Created by Nadif Rizky**

Important: old inline panels sent before the latest update still contain the old non-working inline-query buttons. Send `/start` again to get the new working control panel.

## Project Structure

```text
AUTOPIXEL/
├── main.py
├── config.py
├── requirements.txt
├── README.md
├── core/
│   ├── proxy_manager.py
│   ├── runtime_state.py
│   └── session_manager.py
├── handlers/
│   ├── auth_handlers.py
│   ├── bot_handlers.py
│   ├── offer_handlers.py
│   ├── session_handlers.py
│   ├── states.py
│   └── ui.py
├── services/
│   ├── device_simulator.py
│   ├── google_automation.py
│   ├── network_diagnostics.py
│   ├── device_simulator_core/
│   └── google_automation_core/
└── assets/
    └── telegram/
        └── pixel-header.png
```

## Requirements

- Python 3.10+
- Google Chrome installed
- A Telegram bot token from `@BotFather`
- Internet connection
- Optional: `proxies.txt` if you want proxy mode

## Local Setup

### 1. Create and activate virtualenv

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment

Copy `.env.example` to `.env` and fill what you need:

```env
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
BOT_HEADER_MEDIA_URL=
CHROME_BIN=
CHROMEDRIVER_PATH=
PROXY_ENABLED=1
PROXY_FILE_PATH=
PROXY_FAILURE_COOLDOWN_SECONDS=90
PROXY_QUARANTINE_SECONDS=300
PROXY_QUARANTINE_THRESHOLD=3
```

Notes:

- `BOT_HEADER_MEDIA_URL` supports a local image path, image URL, GIF URL, or MP4 URL
- if `BOT_HEADER_MEDIA_URL` is empty, the bot uses the bundled local banner asset
- if `CHROMEDRIVER_PATH` is empty, Selenium Manager fallback is used

### 4. Optional: add proxies

Create `proxies.txt` in the project root if you want proxy mode.

Supported formats:

```text
http://ip:port
http://user:pass@ip:port
https://user:pass@ip:port
socks5://ip:port
ip:port:user:pass
user:pass@ip:port
```

### 5. Run the bot

```powershell
python main.py
```

## Typical Flow

1. Send `/start`
2. Send `/lang_id` if you want Indonesian UI
3. Send `/login`
4. Enter email
5. Enter password, or `password|totp_secret`
6. Check `/ip` or `/proxy`
7. Send `/check_offer`
8. If 2FA is requested, send the 6-digit code in Telegram
9. Review the result or debug artifacts

## Success Example

This is a simple example so users can recognize a normal successful flow:

```text
You: /start
Bot: Pixel Control Panel opens

You: /login
Bot: Please enter your Google email address

You: user@gmail.com
Bot: Email accepted. Now send your password

You: yourpassword
Bot: ✅ Session Ready
Bot: A fresh Pixel 10 Pro profile is ready for this session

You: /check_offer
Bot: ⏳ Starting secure check...
Bot: 🌍 Active Proxy Panel ...
Bot: ✅ Login successful
Bot: 🎉 Gemini Pro Offer Found! 🔗 https://one.google.com/...
```

## How Users Know It Worked

- Login step is successful when the bot shows `✅ Session Ready`
- Proxy/direct check is successful when `/ip` or `/proxy` shows the active network identity
- Offer check is successful when the bot shows `🎉 Gemini Pro Offer Found!`
- If no offer exists, the bot will say no active offer was found and may attach screenshot/HTML debug artifacts

## Proxy and IP Notes

- `/proxy` shows the active proxy for the session and pool availability
- `/ip` shows the effective network identity
- `/disable_proxy` locks the session to direct/local IP
- `/rotate_proxy` re-enables proxy mode for the session and chooses another proxy
- when proxy transport fails, `/check_offer` can rotate automatically

## Debug Artifacts

When no offer is found, the bot can save:

- screenshot `.png`
- page source `.html`

Artifacts are stored under:

```text
logs/offer_debug/chat_<chat_id>/
```

This helps distinguish:

- no eligible promo
- regular paid Google AI Pro plan only
- page rendering or scanner mismatch

## BotFather Copy

### Short Description

```text
Pixel 10 Pro Google One assistant with login automation, proxy tools, IP diagnostics, and Gemini offer checking.
```

### Description

```text
This bot helps you manage secure Google One / Gemini offer checks with a modern Pixel-style control panel.

✅ Secure Login: Save a session and launch Google sign-in safely
✅ Offer Check: Scan Google One pages for Gemini / AI Pro offer availability
✅ Proxy Tools: Rotate proxy, disable proxy, or inspect IP identity in real time
✅ Session Status: Review account, device, and connection details instantly

Tap /start to open the Pixel Control Panel.

Created by Nadif Rizky.
```

## Security Notes

- Credentials are kept in memory for the active session only
- Passwords are wiped after use in the offer-check flow
- Sessions expire automatically after the configured TTL
- Automation may still trigger Google security challenges depending on account risk and region context

## Troubleshooting

| Problem | Likely Cause | Next Step |
|---|---|---|
| `No module named 'telegram'` | You ran global Python instead of the project virtualenv | Activate `.venv` and run `python main.py` again |
| `409 Conflict` | More than one bot instance is running | Stop duplicate `main.py` processes |
| `/check_offer` says no credentials | Session password already cleared | Run `/login` again |
| Proxy selected but IP still direct | Session is in direct mode or no proxy assigned | Use `/proxy`, `/ip`, or `/rotate_proxy` |
| Proxy precheck fails | Bad proxy / blocked route | Rotate proxy or replace proxy pool |
| No offer found | Account not eligible, wrong billing context, or promo already used | Check account region, payments profile, and offer history |

## Disclaimer

Use this project responsibly and only with accounts you own or are authorized to use. Automation against third-party services may be restricted by their policies or terms.
