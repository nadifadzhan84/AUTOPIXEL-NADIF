"""Shared runtime controls for rate limiting and concurrency."""

import asyncio

# Per-user cooldown: maps chat_id -> last /check_offer timestamp
LAST_CHECK_TIME: dict[int, float] = {}
CHECK_OFFER_COOLDOWN = 5 * 60  # 5 minutes between checks per user

# Limit the number of simultaneous Chrome instances (1 for <=4GB RAM servers)
CHROME_SEMAPHORE = asyncio.Semaphore(1)
