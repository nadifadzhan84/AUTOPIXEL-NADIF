# Changelog

This file documents the feature baseline of AutoPixel.

## [1.0.0] - 2026-03-26

### Product Scope
- Telegram-first automation workflow for Google One Gemini promotional offer checks
- Pixel 10 Pro device simulation profile with anti-detection oriented browser attributes
- Offer eligibility automation for user-provided Google accounts

### Core Features
- Account login conversation flow:
  - `/login` captures email and password interactively
  - Optional combined credential input format: `password|totp_secret`
- Offer check flow:
  - `/check_offer` launches browser automation and checks Google One offer pages
  - Multi-attempt retry strategy with fresh device profile per attempt
  - Structured user feedback during each attempt
- Session utilities:
  - `/status` returns account/session/device summary
  - `/get_link` returns last captured activation URL
  - `/logout` securely clears session and credentials
- 2FA handling:
  - TOTP auto-generation when secret is provided
  - Manual 2FA code input fallback when required
  - Timeout and cancellation handling for pending 2FA flow

### Architecture
- Modular project layout:
  - `core/` for runtime state and session lifecycle
  - `handlers/` for Telegram commands and UX flow
  - `services/` for automation and simulation business logic
- Internal service decomposition:
  - `services/google_automation_core/` for driver, login, scanner, and API modules
  - `services/device_simulator_core/` for generators, constants, profile, and factory modules
- Facade modules retained for clean external imports:
  - `services/google_automation.py`
  - `services/device_simulator.py`

### Bot UX
- Modernized command UX with persistent main menu keyboard
- Inline quick actions for frequent commands
- Localized language preference switch commands:
  - `/lang_en`
  - `/lang_id`
- Message templates centralized through UI helper utilities for cleaner handler code
- Consistent status/error/progress messaging style across auth and offer flows

### Reliability and Safety
- Session credential storage uses in-memory `bytearray` values
- Secure wipe routine for credentials at flow termination
- Password and sensitive code chat message deletion attempts
- Per-user cooldown for offer checks
- Concurrency limiting for browser sessions to reduce resource contention

### Runtime and Platform Support
- Cross-platform runtime support:
  - Windows
  - Linux
  - macOS
- Browser/driver detection strategy:
  - Auto-detect browser binaries where possible
  - Support explicit `CHROME_BIN`
  - Support explicit `CHROMEDRIVER_PATH`
  - Selenium Manager fallback when driver path is not manually set

### Deployment
- Dockerized runtime with Chromium/Chromedriver support
- Compose service standardized to container name: `autpixel`
- `.env.example` provided for required and optional environment setup

### Documentation Baseline
- README redesigned with:
  - Product-style overview and highlights
  - Region support matrix
  - Eligibility checklist
  - Troubleshooting by symptom
  - Local and Docker quick-start guidance
