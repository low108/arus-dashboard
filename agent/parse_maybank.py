"""Read a Maybank account statement into the ledger format.

This layout differs from a card statement in four ways that all break a
naive reader:

  * The sign trails the number: "7.35-" is money out, "50.00+" is money in.
  * There is a running balance column, which lets every single row be checked
    rather than just the final total.
  * One transaction can span several lines - the counterparty name and
    reference sit underneath with no date of their own.
  * Dates are DD/MM/YY.

Rows are found by pattern rather than by column position, so this survives
a bank moving its columns between statement versions.

    python parse_maybank.py statement.pdf --password <pw> --csv out.csv
"""

import argparse
import csv
import os
import re
import sys

import pymupdf

DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{2})$")
SIGNED = re.compile(r"^([\d,]+\.\d{2})([+-])$")
PLAIN = re.compile(r"^[\d,]+\.\d{2}$")

# Page furniture is now excluded by the indent rule, so this only needs to
# catch table furniture sitting at the same indent. Keep it narrow: a broad
# list once stripped "MAYBANK VISA CARD" out of a card repayment line, which
# is the one thing that identifies it as a repayment.
SKIP = re.compile(
    r"^(beginning|ending) balance|^total (credit|debit)|"
    r"account transactions|urusniaga akaun", re.I)


def lines_of(page):
    """Group words into visual lines. Returns (left edge, words) per line."""
    rows = {}
    for x0, y0, _x1, _y1, word, *_ in page.get_text("words"):
        rows.setdefault(round(y0 / 3), []).append((x0, word))
    out = []
    for _y, items in sorted(rows.items()):
        items.sort()
        out.append((items[0][0], [w for _x, w in items]))
    return out


def is_transaction(tokens):
    """A dated row carrying a signed amount."""
    if not tokens or not DATE.match(tokens[0]):
        return None
    for i, token in enumerate(tokens):
        if SIGNED.match(token):
            return i
    return None


def find_continuation_indent(pages):
    """Work out where continuation lines start on this particular statement.

    Continuations sit at one consistent left edge, indented under the
    description. Page headers, addresses and footers all sit elsewhere, so
    the most common left edge among lines following a transaction is the
    one we want. Learning it per file means a bank moving its columns does
    not break this.
    """
    tally = {}
    for lines in pages:
        after_transaction = False
        for left, tokens in lines:
            if is_transaction(tokens) is not None:
                after_transaction = True
                continue
            if after_transaction and tokens:
                tally[round(left, 1)] = tally.get(round(left, 1), 0) + 1
    return max(tally, key=tally.get) if tally else None


def parse(path, password=None, year_prefix="20"):
    doc = pymupdf.open(path)
    if doc.needs_pass and not doc.authenticate(password or ""):
        sys.exit("Password rejected. Pass --password or set STATEMENT_PASSWORD.")

    pages = [lines_of(page) for page in doc]
    indent = find_continuation_indent(pages)

    transactions = []
    opening = None
    stated = {}

    for lines in pages:
        for left, tokens in lines:
            if not tokens:
                continue
            text = " ".join(tokens)
            upper = text.upper()

            if opening is None and "BEGINNING BALANCE" in upper:
                numbers = [t for t in tokens if PLAIN.match(t)]
                if numbers:
                    opening = float(numbers[-1].replace(",", ""))
                continue

            # The statement's own totals, for checking our arithmetic against.
            for phrase, key in (("ENDING BALANCE", "closing"),
                                ("TOTAL CREDIT", "credit"),
                                ("TOTAL DEBIT", "debit")):
                if phrase in upper:
                    numbers = [t for t in tokens if PLAIN.match(t)]
                    if numbers:
                        stated[key] = float(numbers[-1].replace(",", ""))

            index = is_transaction(tokens)
            if index is not None:
                amount_text, sign = SIGNED.match(tokens[index]).groups()
                amount = float(amount_text.replace(",", ""))
                tail = [t for t in tokens[index + 1:] if PLAIN.match(t)]
                day, month, yy = DATE.match(tokens[0]).groups()

                transactions.append({
                    "trans_date": f"{day}/{month}",
                    "post_date": f"{day}/{month}",
                    "year": int(year_prefix + yy),
                    "description": " ".join(tokens[1:index]).strip(),
                    # Our ledger counts money leaving as positive.
                    "amount": amount if sign == "-" else -amount,
                    "direction": "debit" if sign == "-" else "credit",
                    "balance": float(tail[-1].replace(",", "")) if tail else None,
                    "category": "",
                    "note": "",
                })
                continue

            # A continuation only counts if it sits at the indent this
            # statement uses. Everything else on the page - running headers,
            # the address block, the small print - starts somewhere else.
            if not transactions or indent is None or abs(left - indent) > 3:
                continue
            if SKIP.search(text) or not re.search(r"[A-Za-z]", text):
                continue
            extra = " ".join(text.split())
            if 1 < len(extra) < 60:
                transactions[-1]["description"] = (
                    transactions[-1]["description"] + " " + extra).strip()

    doc.close()
    return opening, transactions, stated


def check_running_balance(opening, transactions):
    """The balance column means every row can be verified, not just the total."""
    if opening is None:
        return None
    running = opening
    problems = []
    for i, t in enumerate(transactions):
        running = round(running - t["amount"], 2)
        if t["balance"] is not None and abs(running - t["balance"]) > 0.005:
            problems.append((i + 1, t["description"][:38], running, t["balance"]))
            running = t["balance"]      # resync so one gap isn't reported twice
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--password", default=os.environ.get("STATEMENT_PASSWORD"))
    ap.add_argument("--csv", default="maybank.csv")
    ap.add_argument("--account", default="Maybank Savings")
    ap.add_argument("--kind", default="deposit", choices=["deposit", "card"])
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    opening, transactions, stated = parse(args.pdf, args.password)
    if not transactions:
        sys.exit("No transactions found. Send me the first page's text and "
                 "I will adjust the patterns.")

    for t in transactions:
        t["account"] = args.account
        t["account_kind"] = args.kind

    fields = ["account", "account_kind", "trans_date", "post_date", "year",
              "description", "amount", "direction", "category", "note",
              "balance"]
    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(transactions)

    out = sum(t["amount"] for t in transactions if t["amount"] > 0)
    into = sum(-t["amount"] for t in transactions if t["amount"] < 0)
    print(f"{len(transactions)} transactions -> {args.csv}")
    print(f"  opening balance {opening if opening is not None else 'not found'}")
    print(f"  money out {out:>12,.2f}", end="")
    if "debit" in stated:
        ok = "matches" if abs(out - stated["debit"]) < 0.005 else "DOES NOT MATCH"
        print(f"   statement says {stated['debit']:,.2f}  {ok}")
    else:
        print()
    print(f"  money in  {into:>12,.2f}", end="")
    if "credit" in stated:
        ok = "matches" if abs(into - stated["credit"]) < 0.005 else "DOES NOT MATCH"
        print(f"   statement says {stated['credit']:,.2f}  {ok}")
    else:
        print()

    problems = check_running_balance(opening, transactions)
    if problems is None:
        print("\n  no opening balance found, so rows could not be verified")
    elif problems:
        print(f"\n  {len(problems)} row(s) do not match the balance column:")
        for row_no, desc, expected, actual in problems[:10]:
            print(f"    row {row_no}: {desc}  expected {expected:,.2f}, "
                  f"statement says {actual:,.2f}")
    else:
        print("\n  every row agrees with the running balance column")


if __name__ == "__main__":
    main()
