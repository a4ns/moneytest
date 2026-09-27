#!/usr/bin/env python3
"""Superteam Earn screener (internal tool).

Open bounties we are eligible for (Global / Kazakhstan), paid in cash tokens,
deadline early enough to be paid before the finish date. Ranked by a rough EV.

Base rates (May–Sep 2026, 95 global cash bounties): median 94 submissions,
5 prize spots, $100 per spot; winners announced median 7 days after deadline
(p75 16, p90 25).

Usage: python3 tools/superteam_scan.py [--last-deadline 2026-10-20] [--usd 441.88]
"""
import argparse
import datetime as dt
import json
import re
import time
import urllib.request

BASE = "https://earn.superteam.fun/api/listings"
UA = {"User-Agent": "Mozilla/5.0"}
CASH = {"USDC", "USDT", "SOL", "USDG"}
FORMATS = {
    "X": r"\bX\b|twitter|thread|tweet",
    "video": r"video|youtube|tiktok|reel",
    "article": r"article|blog|medium|substack|mirror|essay",
    "code": r"github|repo|deploy|build|sdk|smart contract|program",
    "design": r"figma|design|logo|merch|ui\b|ux\b",
}


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--last-deadline", default="2026-10-20")
    ap.add_argument("--usd", type=float, default=441.88)
    ap.add_argument("--our-edge", type=float, default=2.0, help="our win odds vs a random submission")
    a = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for x in get(f"{BASE}/?take=300"):
        if x["type"] != "bounty" or x["status"] != "OPEN" or not x["deadline"]:
            continue
        if x["deadline"][:10] > a.last_deadline or x["token"] not in CASH:
            continue
        d = get(f"{BASE}/details/{x['slug']}")
        if d.get("region") not in ("Global", "Kazakhstan"):
            continue
        desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", d.get("description") or ""))
        if re.search(r"ticket in place of|no cash prize", desc, re.I):
            continue
        rewards = d.get("rewards") or {}
        spots = len([k for k in rewards if k != "99"]) + (d.get("maxBonusSpots") or 0)
        prize = sum(v for k, v in rewards.items() if k != "99") or x["rewardAmount"] or 0
        subs = x["_count"]["Submission"]
        days_left = max(0.0, (dt.datetime.fromisoformat(x["deadline"].replace("Z", "+00:00")) - now).days)
        final_subs = max(10, subs + 6 * days_left)  # most entries arrive near the deadline
        p = min(0.6, a.our_edge * spots / final_subs)
        ev = p * prize / max(1, spots) * a.usd
        fmt = ",".join(k for k, pat in FORMATS.items() if re.search(pat, desc, re.I))
        no_ai = bool(re.search(r"ai[- ]generated|no ai|without ai|chatgpt", desc, re.I))
        rows.append((ev, x["deadline"][:10], x["token"], prize, spots, subs, p, fmt, no_ai,
                     d.get("region"), x["title"], x["slug"]))

    rows.sort(reverse=True)
    for ev, dl, tok, prize, spots, subs, p, fmt, no_ai, region, title, slug in rows:
        flag = " ⚠AI-правило" if no_ai else ""
        print(f"EV≈{ev:,.0f} ₸ | p≈{p:.0%} | ${prize:,.0f} {tok} на {spots} мест | {subs} заявок | до {dl} | "
              f"{region} | {fmt}{flag}\n  {title}\n  https://earn.superteam.fun/listing/{slug}\n")
    print(f"итого подходящих: {len(rows)}")


if __name__ == "__main__":
    main()
