"""Extract transactions from a password-protected card statement into CSV.

Uses positioned text (word boxes) rather than the flat text stream, so columns
are recovered by x-coordinate and rows by y-coordinate. Continuation lines that
carry no date attach to the transaction above them.

Usage:
    python parse_statement.py STATEMENT.pdf --csv out.csv
    STATEMENT_PASSWORD is read from the environment if --password is omitted.
"""

import argparse
import csv
import os
import re
import sys

import pymupdf

# Column boundaries in points, measured from the statement layout.
COL_POST = 95
COL_DESC = 143
COL_AMOUNT = 400

# Vertical band holding the table body. Excludes the running header and the
# footer disclaimer, whose words would otherwise land in the description column.
BODY_TOP = 100
BODY_BOTTOM = 760

# A continuation line must sit directly beneath the transaction it belongs to.
CONTINUATION_GAP = 20

DATE = re.compile(r"^\d{2}/\d{2}$")
MONEY = re.compile(r"^-?[\d,]+\.\d{2}$")

CATEGORIES = {
    "transport": ["grab* ride", "petronas", "touch n go", "rapid", "mrt"],
    "groceries": ["lotus's", "tesco", "aeon", "jaya grocer", "village grocer"],
    "dining": ["starbucks", "mcdonald", "foodpanda", "grab* food", "kfc"],
    "shopping": ["shopee", "lazada", "watsons", "uniqlo", "zalora"],
    "subscriptions": ["netflix", "spotify", "youtube", "apple.com", "google"],
    "utilities": ["tnb", "syabas", "unifi", "maxis", "celcom", "digi"],
    "entertainment": ["cinema", "gsc", "tgv", "steam"],
    "fees": ["annual fee", "finance charge", "late payment", "service tax"],
    "housing": ["rent payment", "property mgmt", "maintenance fee"],
    "insurance": ["insurance", "takaful", "ge life", "prudential"],
}


def categorise(description):
    low = description.lower()
    for name, keys in CATEGORIES.items():
        if any(k in low for k in keys):
            return name
    return "uncategorised"


def rows_from_page(page):
    """Group word boxes into rows keyed by vertical position."""
    lines = {}
    for x0, y0, _x1, _y1, word, *_ in page.get_text("words"):
        if not BODY_TOP < y0 < BODY_BOTTOM:
            continue
        lines.setdefault(round(y0), []).append((x0, word))

    out = []
    for y in sorted(lines):
        cells = {"trans": [], "post": [], "desc": [], "amount": []}
        for x0, word in sorted(lines[y]):
            if x0 < COL_POST:
                cells["trans"].append(word)
            elif x0 < COL_DESC:
                cells["post"].append(word)
            elif x0 < COL_AMOUNT:
                cells["desc"].append(word)
            else:
                cells["amount"].append(word)
        row = {k: " ".join(v) for k, v in cells.items()}
        row["y"] = y
        out.append(row)
    return out


def parse(path, password):
    doc = pymupdf.open(path)
    if doc.needs_pass and not doc.authenticate(password):
        sys.exit("Password rejected. Check --password or STATEMENT_PASSWORD.")

    transactions = []
    for page in doc:
        last_y = None
        for row in rows_from_page(page):
            trans, post, desc, amount = (row["trans"], row["post"],
                                         row["desc"], row["amount"])

            # Continuation line: description only, no dates, no amount, and
            # sitting directly under the transaction it belongs to.
            if desc and not DATE.match(trans) and not amount:
                near = last_y is not None and 0 < row["y"] - last_y <= CONTINUATION_GAP
                if transactions and near:
                    transactions[-1]["note"] = desc.strip()
                continue

            if not DATE.match(trans) or not amount:
                continue

            is_credit = amount.upper().endswith("CR")
            figure = amount.upper().replace("CR", "").strip()
            if not MONEY.match(figure):
                continue

            value = float(figure.replace(",", ""))
            clean = " ".join(desc.split())
            if is_credit:
                category = "refund" if "refund" in clean.lower() else "payment"
            else:
                category = categorise(clean)

            transactions.append({
                "trans_date": trans,
                "post_date": post,
                "description": clean,
                "amount": -value if is_credit else value,
                "direction": "credit" if is_credit else "debit",
                "category": category,
                "note": "",
            })
            last_y = row["y"]

    doc.close()
    return transactions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--password", default=os.environ.get("STATEMENT_PASSWORD"))
    ap.add_argument("--csv", default="transactions.csv")
    ap.add_argument("--account", default="unknown",
                    help="account label applied to every row")
    ap.add_argument("--kind", default="card", choices=["card", "deposit"])
    args = ap.parse_args()

    if not args.password:
        sys.exit("No password. Pass --password or set STATEMENT_PASSWORD.")

    txns = parse(args.pdf, args.password)
    if not txns:
        sys.exit("No transactions found. Column boundaries may need adjusting.")

    for t in txns:
        t["account"] = args.account
        t["account_kind"] = args.kind

    fields = ["account", "account_kind", "trans_date", "post_date",
              "description", "amount", "direction", "category", "note"]
    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(txns)

    debits = sum(t["amount"] for t in txns if t["amount"] > 0)
    credits = -sum(t["amount"] for t in txns if t["amount"] < 0)

    print(f"{len(txns)} transactions -> {args.csv}")
    print(f"  debits  {debits:>10,.2f}")
    print(f"  credits {credits:>10,.2f}")
    print(f"  net     {debits - credits:>10,.2f}")
    print()
    for name in sorted({t["category"] for t in txns}):
        total = sum(t["amount"] for t in txns if t["category"] == name
                    and t["amount"] > 0)
        if total:
            print(f"  {name:<16} {total:>9,.2f}")


if __name__ == "__main__":
    main()
