#!/usr/bin/env python3
"""
Free iPhone Duo stock alert - Apple India official store (apple.com/in).

Checks Apple India's own "pick up in store" availability for the
iPhone Duo 512GB Star White at Apple Noida and Apple Saket, and pushes an
alert to your phone (ntfy app, free) the moment it shows as available.
Tapping the alert opens the Apple India store page.

Two ways to run:
  1. On your Mac:    python3 duo_stock_alert.py          (loops until Ctrl+C)
  2. In the cloud:   GitHub Actions runs it with --once every ~5 minutes
                     (see .github/workflows/duo-alert.yml)

Standard library only - nothing to install.
"""

import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

# ---- settings -------------------------------------------------------------
PART = "MK2F4HN/A"                    # iPhone Duo, Star White, 512GB (India)
LOCATION = "201301"                   # Noida PIN; Apple also returns Saket
STORES_WANTED = ["noida", "saket"]    # matched against Apple store names
CHECK_EVERY_SECONDS = 120             # Mac loop interval (don't go below ~90)
# Your private ntfy topic. Subscribe to this exact name in the ntfy app.
# In GitHub Actions it's read from the NTFY_TOPIC secret instead.
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "eashan-duo-x7k29q")
BUY_PAGE = "https://www.apple.com/in/shop/buy-iphone"
# ---------------------------------------------------------------------------

URL = "https://www.apple.com/in/shop/fulfillment-messages?" + urllib.parse.urlencode({
    "pl": "true",
    "mts.0": "regular",
    "parts.0": PART,
    "location": LOCATION,
})
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "application/json",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.apple.com/in/shop/buy-iphone",
}


def push_phone(title, message, priority="urgent"):
    if not NTFY_TOPIC:
        return
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode(),
            headers={"Title": title, "Priority": priority,
                     "Tags": "iphone,rotating_light", "Click": BUY_PAGE})
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print("  (phone push failed:", e, ")")


def notify(title, message):
    print(f"\a*** {title}: {message}")
    push_phone(title, message)
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e",
                        f'display notification "{message}" with title "{title}" sound name "Glass"'])
        subprocess.run(["say", "iPhone Duo in stock"])


def check():
    """Returns list of 'Store: quote' strings where the part is available."""
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode()
    data = json.loads(raw)
    stores = (data.get("body", {}).get("content", {})
                  .get("pickupMessage", {}).get("stores", []))
    if not stores:
        raise RuntimeError("Unexpected response from Apple: " + raw[:300])
    hits = []
    for s in stores:
        name = s.get("storeName", "")
        if not any(w in name.lower() for w in STORES_WANTED):
            continue
        part = s.get("partsAvailability", {}).get(PART, {})
        status = part.get("pickupDisplay", "?")
        quote = part.get("pickupSearchQuote", "")
        print(f"  {name}: {status}{(' - ' + quote) if quote else ''}")
        if status == "available":
            hits.append(f"Apple {name}: {quote or 'available'}")
    return hits


def run_once():
    print(datetime.now().strftime("%H:%M:%S"), "checking...")
    hits = check()
    if hits:
        notify("iPhone Duo 512GB White IN STOCK",
               " | ".join(hits) + " - tap to open Apple Store, reserve pickup NOW")
    return bool(hits)


def main():
    args = sys.argv[1:]
    if "--test" in args:
        push_phone("Test alert", "Duo alert is set up. Tap to open Apple India store.", "default")
        print("Test alert sent to ntfy topic:", NTFY_TOPIC)
        return
    if "--once" in args:
        # Cloud mode: a few checks spread over ~5 minutes, then exit.
        rounds = int(os.environ.get("ROUNDS", "4"))
        failures = 0
        for i in range(rounds):
            try:
                run_once()
            except Exception as e:
                failures += 1
                print("  Check failed:", e)
            if i < rounds - 1:
                time.sleep(70)
        if failures == rounds:
            sys.exit(1)   # makes the GitHub run show red so you notice
        return
    print(f"Watching {PART} at {STORES_WANTED} every {CHECK_EVERY_SECONDS}s "
          f"(phone topic: {NTFY_TOPIC}). Ctrl+C to stop.")
    push_phone("Duo alert started", "Watching Apple Noida & Saket.", "low")
    while True:
        try:
            run_once()
        except Exception as e:
            print("  Check failed:", e)
        time.sleep(CHECK_EVERY_SECONDS)


if __name__ == "__main__":
    main()
