#!/usr/bin/env python3
"""Render one page per lead from leads.csv with a Jinja2 template (internal tool).

Usage: python3 tools/demo/render.py leads.csv --template site.html.j2 --out out/
Static files next to the template (templates/static/*) are copied into every page folder.
"""
import argparse
import csv
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = Path(__file__).parent
TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюяәғқңөұүһі",
                    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "i", "k", "l", "m", "n", "o", "p", "r", "s",
                     "t", "u", "f", "h", "c", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya", "a", "g", "k", "n",
                     "o", "u", "u", "h", "i"]))


def slug(text):
    s = "".join(TRANSLIT.get(ch, ch) for ch in text.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "lead"


def services(raw):
    """'Маникюр — 5000; Педикюр — 7000' -> [{'name': 'Маникюр', 'price': '5 000'}, ...]"""
    out = []
    for part in filter(None, (p.strip() for p in (raw or "").split(";"))):
        name, _, price = part.partition("—") if "—" in part else part.partition("-")
        digits = re.sub(r"\D", "", price)
        out.append({"name": name.strip(), "price": f"{int(digits):,}".replace(",", " ") if digits else price.strip()})
    return out


def context(row):
    phone = re.sub(r"\D", "", row.get("whatsapp") or row.get("phone") or "")
    if phone.startswith("8") and len(phone) == 11:
        phone = "7" + phone[1:]
    return {**row, "slug": slug(f"{row['name']} {row.get('city', '')}"), "services": services(row.get("services")),
            "wa": f"https://wa.me/{phone}" if phone else "", "phone_digits": phone}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("leads")
    ap.add_argument("--template", default="site.html.j2")
    ap.add_argument("--out", default=str(HERE / "out"))
    a = ap.parse_args()

    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html", "j2"]))
    tpl = env.get_template(a.template)
    static = HERE / "templates" / "static"
    out = Path(a.out)
    with open(a.leads, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not (row.get("name") or "").strip():
                continue
            ctx = context(row)
            page = out / ctx["slug"]
            page.mkdir(parents=True, exist_ok=True)
            (page / "index.html").write_text(tpl.render(**ctx), encoding="utf-8")
            if static.is_dir():
                shutil.copytree(static, page / "static", dirs_exist_ok=True)
            print(page)


if __name__ == "__main__":
    main()
