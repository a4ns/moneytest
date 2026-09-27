#!/usr/bin/env python3
"""Kwork project-board scanner (internal tool).

Reads the public board, keeps fresh projects we can deliver with AI
(sites, scripts, bots, texts, translations, presentations), few offers so far.

Usage: python3 tools/kwork_scan.py [--pages 8] [--hours 6] [--max-offers 6] [--min-budget 1000]
"""
import argparse
import datetime as dt
import json
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/141.0 Safari/537.36"}
MSK = dt.timezone(dt.timedelta(hours=3))

GOOD = re.compile(
    r"сайт|лендинг|landing|tilda|тильд|html|верст|парс|бот|telegram|телеграм|скрипт|python|"
    r"автоматиз|google ?(sheets|таблиц)|excel|таблиц|api|интеграц|нейросет|gpt|chatgpt|ии\b|"
    r"презентац|pitch|питч|перев|english|англ|казах|текст|статья|описани|карточ|seo-текст|"
    r"резюме|инструкц|документац|расшифр|транскриб", re.I)
BAD = re.compile(
    r"1с|1c|bitrix|битрикс|звонк|обзвон|продаж|менеджер по|ассистент руководителя|курьер|"
    r"монтаж|видео|reels|after effects|озвуч|голос|фото|3d|логотип|иллюстрац|smm-менеджер|"
    r"таргет|директ|авито|отзыв|накрут|ставк|казино|крипт|партнёрск|партнерск|"
    # не берём: спам, обход защит, чужие аккаунты, нарушение авторских прав
    r"рассылк|спам|капч|captcha|отпечат|fingerprint|антидетект|водян|игров\w* бот|зарегистрир|аккаунт", re.I)


def fetch(page):
    url = f"https://kwork.ru/projects?c=all&page={page}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        t = r.read().decode("utf-8", "ignore")
    i = t.index("{", t.index("window.stateData"))
    state, _ = json.JSONDecoder().raw_decode(t[i:])
    w = state["wantsListData"]
    return w.get("wants") or (w.get("pagination") or {}).get("data") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=8)
    ap.add_argument("--hours", type=float, default=6)
    ap.add_argument("--max-offers", type=int, default=6)
    ap.add_argument("--min-budget", type=int, default=1000)
    a = ap.parse_args()

    now = dt.datetime.now(MSK)
    seen, rows = set(), []
    for p in range(1, a.pages + 1):
        for x in fetch(p):
            if x["id"] in seen:
                continue
            seen.add(x["id"])
            created = x.get("date_create") or ""
            try:
                age_h = (now - dt.datetime.fromisoformat(created).replace(tzinfo=MSK)).total_seconds() / 3600
            except ValueError:
                age_h = None
            text = f"{x['name']} {x.get('description', '')}"
            budget = int(float(x.get("priceLimit") or 0))
            if (age_h is not None and age_h > a.hours) or int(x.get("kwork_count") or 0) > a.max_offers:
                continue
            if budget < a.min_budget or not GOOD.search(text) or BAD.search(text):
                continue
            rows.append((age_h or 0, budget, int(x.get("possiblePriceLimit") or budget), int(x["kwork_count"]),
                         x["id"], x["name"], re.sub(r"\s+", " ", x.get("description", ""))[:220]))

    rows.sort(key=lambda r: (r[3], -r[1]))
    for age, budget, maxb, offers, pid, name, desc in rows:
        print(f"[{offers} откл | {budget}–{maxb} ₽ | {age:.1f} ч] {name}\n  https://kwork.ru/projects/{pid}\n  {desc}\n")
    print(f"итого подходящих: {len(rows)} из {len(seen)} просмотренных")


if __name__ == "__main__":
    main()
