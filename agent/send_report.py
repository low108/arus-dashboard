"""Read the ledger from Google Sheets, build the report card, send it to Telegram.

    python send_report.py --dry-run     build the image, don't send
    python send_report.py               build and send
    python send_report.py --local ledger.csv    skip the sheet, use a file

Settings come from a file called .env sitting next to this script.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import consolidate
import sorter

HERE = Path(__file__).parent

CATEGORY_EMOJI = {
    "housing": "🏠", "groceries": "🛒", "shopping": "🛍️", "insurance": "🛡️",
    "fees": "🧾", "transport": "🚗", "utilities": "💡", "dining": "🍜",
    "subscriptions": "📺", "entertainment": "🎬", "health": "💊",
    "education": "📚", "travel": "✈️", "cash": "🏧", "gifts": "🎁",
    "other": "📦", "investing": "📈", "uncategorised": "❓",
}
CATEGORY_LABEL = {
    "fees": "Bank fees", "dining": "Eating out", "entertainment": "Fun",
    "cash": "Cash out", "other": "Everything else",
    "uncategorised": "Not sorted yet",
}
EXCLUSION_EMOJI = {
    "card_repayment": "💳", "internal_transfer": "🏦", "refund": "↩️",
    "investment": "📈",
}
# The bank's own wording is shouty and full of account numbers. Say it plainly.
EXCLUSION_LABEL = {
    "card_repayment": "Paying off the credit card",
    "internal_transfer": "Moved into your savings",
    "refund": "A refund that came back",
    "investment": "Put into investments",
}


def load_env():
    path = HERE / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def pull_sheet(out_csv):
    """Ask the Versa sheets helper for the current ledger tab."""
    helper = os.environ.get("SHEETS_HELPER")
    if not helper:
        sys.exit("SHEETS_HELPER is required when --local is not supplied")
    tab = os.environ.get("SHEET_TAB", "Arus Ledger")

    command = [sys.executable, helper, "read", "--tab", tab]
    sheet = os.environ.get("SHEET_URL")
    if sheet:
        command += ["--sheet", sheet]

    result = subprocess.run(command, capture_output=True, text=True,
                            encoding="utf-8")
    if result.returncode != 0:
        sys.exit(f"Could not read the sheet:\n{result.stderr.strip()}")

    out_csv.write_text(result.stdout, encoding="utf-8")
    return out_csv


def money(value):
    return f"{value:,.2f}"


def exclusions_html(facts):
    blocks = []
    for e in facts["exclusions"]:
        icon = EXCLUSION_EMOJI.get(e["kind"], "•")
        label = EXCLUSION_LABEL.get(e["kind"], e["label"])
        flag = ('&nbsp;<span class="check">👀 check this one</span>'
                if e["needs_review"] else "")
        blocks.append(f"""      <div class="exrow">
        <div class="exicon">{icon}</div>
        <div class="examt">{facts['currency']} {money(e['amount'])}</div>
        <div style="display: flex; flex-direction: column; gap: 3px;">
          <div class="exlabel">{label}{flag}</div>
          <div class="exwhy">{e['reason']}</div>
        </div>
      </div>""")
    return "\n".join(blocks)


def categories_html(facts):
    rows = []
    for name, amount in facts["spending_by_category"].items():
        icon = CATEGORY_EMOJI.get(name, "•")
        label = CATEGORY_LABEL.get(name, name.title())
        dim = ' muted' if name == "uncategorised" else ''
        rows.append(
            f'      <div class="cat">'
            f'<span class="catname{dim}"><span class="caticon">{icon}</span>'
            f'{label}</span>'
            f'<span class="catamt{dim}">{money(amount)}</span></div>')
    return "\n".join(rows)


def build_html(facts):
    template = (HERE / "report_card.html").read_text(encoding="utf-8")
    h = facts["headline"]
    values = {
        "headline": os.environ.get("REPORT_HEADLINE",
                                   "What this month actually cost you"),
        "period_label": facts["period_label"],
        "account_count": facts["account_count"],
        "transaction_count": facts["transaction_count"],
        "currency": facts["currency"],
        "naive_spending": money(h["naive_spending"]),
        "true_spending": money(h["true_spending"]),
        "overstated_by": money(h["overstated_by"]),
        "income": money(facts["income"]),
        "position_change": money(facts["position_change"]),
        "coverage_note": facts["coverage_note"],
        "footer_note": os.environ.get("REPORT_FOOTER", "Source: verified statements."),
        "exclusions": exclusions_html(facts),
        "categories": categories_html(facts),
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def render(html, out_png):
    """Screenshot the card through the copy of Edge already on this machine."""
    from playwright.sync_api import sync_playwright

    tmp = HERE / "_render.html"
    tmp.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge")
            page = browser.new_page(viewport={"width": 640, "height": 900},
                                    device_scale_factor=2)
            page.goto(tmp.resolve().as_uri())
            page.wait_for_timeout(1200)      # let the web fonts arrive
            page.screenshot(path=str(out_png), full_page=True)
            browser.close()
    finally:
        tmp.unlink(missing_ok=True)


def caption(facts):
    h, c = facts["headline"], facts["currency"]
    lines = [
        f"*{facts['period_label']} is done.*",
        "",
        f"Add up every payment and it looks like you spent "
        f"{c} {money(h['naive_spending'])}.",
        f"You actually spent *{c} {money(h['true_spending'])}*. "
        f"The other {c} {money(h['overstated_by'])} was counted twice or "
        f"was never spending.",
        "",
        f"Money in was {c} {money(facts['income'])}, so you are "
        f"{c} {money(facts['position_change'])} better off than when the "
        f"month started.",
    ]
    n = facts["review_count"]
    if n:
        lines += ["", f"👀 {n} item{'s' if n > 1 else ''} "
                      f"need{'' if n > 1 else 's'} you to confirm "
                      f"{'them' if n > 1 else 'it'}. Open the sheet to check."]
    return "\n".join(lines)


def send(png_path, text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        sys.exit("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing from .env")

    boundary = "----arus-boundary"
    body = b""
    for field, value in (("chat_id", chat), ("caption", text),
                         ("parse_mode", "Markdown")):
        body += (f"--{boundary}\r\nContent-Disposition: form-data; "
                 f'name="{field}"\r\n\r\n{value}\r\n').encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; "
             f'name="photo"; filename="report.png"\r\n'
             f"Content-Type: image/png\r\n\r\n").encode()
    body += png_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto", data=body,
        headers={"Content-Type":
                 f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as err:
        sys.exit(f"Telegram said no: {err.read().decode(errors='replace')}")

    if not payload.get("ok"):
        sys.exit(f"Telegram rejected it: {payload}")
    print("Sent.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="build the image but do not send it")
    ap.add_argument("--local", help="use this CSV instead of the sheet")
    ap.add_argument("--out", default="report.png")
    ap.add_argument("--no-sort", action="store_true",
                    help="skip the model sorting step")
    args = ap.parse_args()

    # The Windows console defaults to an encoding that cannot print emoji.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    load_env()

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ledger = (Path(args.local) if args.local
              else pull_sheet(HERE / "_ledger.csv"))
    print(f"[{stamp}] reading {ledger.name}")

    rows = consolidate.load(str(ledger))
    if not args.no_sort:
        sorter.sort_rows(rows)

    facts = consolidate.build(rows)
    (HERE / "facts.json").write_text(json.dumps(facts, indent=2),
                                     encoding="utf-8")

    out_png = HERE / args.out
    render(build_html(facts), out_png)

    h = facts["headline"]
    print(f"  looks like {h['naive_spending']:>10,.2f}")
    print(f"  actually   {h['true_spending']:>10,.2f}")
    print(f"  wrote {out_png.name}")

    if args.dry_run:
        print("\n--- message (not sent) ---")
        print(caption(facts))
    else:
        send(out_png, caption(facts))


if __name__ == "__main__":
    main()
