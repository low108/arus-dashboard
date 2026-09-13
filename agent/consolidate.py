"""Turn a combined transaction ledger into a validated set of report figures.

Every number in the report is computed here. The renderer and any model-written
prose consume facts.json and never do arithmetic of their own.

Rules applied:
  1. Card repayments  - a deposit outflow matched to a credit on a card account.
                        Real money movement, but not spending: the purchases it
                        settles are already counted on the card statement.
  2. Internal transfers - money moved between accounts the user owns. Still
                        theirs, so not spending. Unmatched ones are excluded but
                        flagged, because only one side was imported.
  3. Refunds          - card credits that are not repayments reduce spending.

Usage:
    python consolidate.py ledger.csv --out facts.json
"""

import argparse
import csv
import json
import os
from datetime import datetime

MATCH_WINDOW_DAYS = 3
CARD_HINTS = ("credit card payment", "card payment", "cc payment",
              "visa card", "mastercard", "maybank visa")

# Banks label ordinary outgoing payments "TRANSFER FROM A/C", so the word
# "transfer" proves nothing on its own - a real Maybank statement uses it for
# every DuitNow lunch. What marks a genuine move between your own accounts is
# that the other side is YOU: your name on the counterparty line, or an
# explicit self-transfer marker. Set ACCOUNT_HOLDER to switch this on.
SELF_HINTS = ("self transfer", "own account", "to own a/c")


def load(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for i, r in enumerate(rows):
        r["id"] = i
        r["amount"] = float(r["amount"])
        r["excluded_reason"] = ""
        r["needs_review"] = False
    return rows


def day(row, year=2026):
    d, m = row["trans_date"].split("/")
    return datetime(year, int(m), int(d))


def match_card_repayments(rows):
    """Pair a deposit outflow with the matching credit on a card account."""
    pairs = []
    card_credits = [r for r in rows
                    if r["account_kind"] == "card" and r["amount"] < 0
                    and r["category"] == "payment"]

    for out in rows:
        if out["account_kind"] != "deposit" or out["amount"] <= 0:
            continue
        if not any(h in out["description"].lower() for h in CARD_HINTS):
            continue
        for credit in card_credits:
            if credit.get("_matched"):
                continue
            if abs(abs(credit["amount"]) - out["amount"]) > 0.005:
                continue
            if abs((day(out) - day(credit)).days) > MATCH_WINDOW_DAYS:
                continue
            credit["_matched"] = True
            out["excluded_reason"] = "card repayment"
            credit["excluded_reason"] = "card repayment (other side)"
            pairs.append((out, credit))
            break
    return pairs


def find_transfers(rows, holder=None):
    """Flag movements between the user's own accounts.

    Identified by the counterparty being the account holder, not by the word
    "transfer" - see the note on SELF_HINTS.
    """
    holder = (holder or os.environ.get("ACCOUNT_HOLDER", "")).strip().lower()
    found = []
    for r in rows:
        if r["excluded_reason"] or r["amount"] <= 0:
            continue
        text = r["description"].lower()
        if any(h in text for h in SELF_HINTS) or (holder and holder in text):
            r["excluded_reason"] = "internal transfer"
            # Only one side was imported, so a human should confirm ownership.
            r["needs_review"] = True
            found.append(r)
    return found


def find_investments(rows):
    """Money going into investments is saving, not spending.

    Unlike a card repayment there is no second statement proving where it
    landed, so these are excluded but always flagged for confirmation.
    """
    found = []
    for r in rows:
        if r["excluded_reason"] or r["amount"] <= 0:
            continue
        if r.get("category") == "investing":
            r["excluded_reason"] = "investment"
            r["needs_review"] = True
            found.append(r)
    return found


def find_refunds(rows):
    return [r for r in rows
            if r["amount"] < 0 and r["category"] == "refund"]


def build(rows, holder=None):
    repayments = match_card_repayments(rows)
    transfers = find_transfers(rows, holder)
    investments = find_investments(rows)
    refunds = find_refunds(rows)

    all_outflows = [r for r in rows if r["amount"] > 0]
    naive = sum(r["amount"] for r in all_outflows)

    spend_rows = [r for r in all_outflows if not r["excluded_reason"]]
    gross_spend = sum(r["amount"] for r in spend_rows)
    refund_total = sum(-r["amount"] for r in refunds)
    true_spend = gross_spend - refund_total

    # Money genuinely entering from outside: deposit credits only. Card credits
    # are repayments and refunds, not income.
    income = sum(-r["amount"] for r in rows
                 if r["account_kind"] == "deposit" and r["amount"] < 0
                 and not r["excluded_reason"])

    exclusions = []
    for out, _credit in repayments:
        exclusions.append({
            "label": out["description"],
            "amount": round(out["amount"], 2),
            "reason": "Card repayment. The purchases it settles are already "
                      "counted on the card statement.",
            "kind": "card_repayment",
            "needs_review": False,
        })
    for t in transfers:
        exclusions.append({
            "label": t["description"],
            "amount": round(t["amount"], 2),
            "reason": "Moved between your own accounts, so it is still your "
                      "money.",
            "kind": "internal_transfer",
            "needs_review": t["needs_review"],
        })
    for t in investments:
        exclusions.append({
            "label": t["description"],
            "amount": round(t["amount"], 2),
            "reason": "Put into investments rather than spent, so it is still "
                      "yours. We cannot see the other side, so please confirm.",
            "kind": "investment",
            "needs_review": True,
        })
    for r in refunds:
        exclusions.append({
            "label": r["description"],
            "amount": round(-r["amount"], 2),
            "reason": "Refund received, which reduces what you actually spent.",
            "kind": "refund",
            "needs_review": False,
        })

    by_category = {}
    for r in spend_rows:
        by_category[r["category"]] = round(
            by_category.get(r["category"], 0) + r["amount"], 2)
    for r in refunds:
        if r["category"] in by_category:
            by_category[r["category"]] = round(
                by_category[r["category"]] + r["amount"], 2)

    accounts = sorted({r["account"] for r in rows})
    overstated = naive - true_spend

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "currency": "RM",
        "period_label": os.environ.get("PERIOD_LABEL", "this month"),
        "accounts": accounts,
        "account_count": len(accounts),
        "transaction_count": len(rows),
        "headline": {
            "naive_spending": round(naive, 2),
            "true_spending": round(true_spend, 2),
            "overstated_by": round(overstated, 2),
            "overstated_pct": round(overstated / true_spend * 100, 1)
            if true_spend else 0,
        },
        "income": round(income, 2),
        "position_change": round(income - true_spend, 2),
        "exclusions": sorted(exclusions, key=lambda e: -e["amount"]),
        "spending_by_category": dict(
            sorted(by_category.items(), key=lambda kv: -kv[1])),
        "review_count": sum(1 for e in exclusions if e["needs_review"]),
        "coverage_note": os.environ.get(
            "COVERAGE_NOTE",
            "Figures come from your latest statements. Anything "
            "spent since then is not included."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ledger")
    ap.add_argument("--out", default="facts.json")
    args = ap.parse_args()

    facts = build(load(args.ledger))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(facts, fh, indent=2)

    h = facts["headline"]
    print(f"accounts       {facts['account_count']}  "
          f"({', '.join(facts['accounts'])})")
    print(f"transactions   {facts['transaction_count']}")
    print()
    print(f"looks like     {h['naive_spending']:>10,.2f}")
    print(f"actually       {h['true_spending']:>10,.2f}")
    print(f"overstated by  {h['overstated_by']:>10,.2f}  "
          f"({h['overstated_pct']}%)")
    print()
    for e in facts["exclusions"]:
        flag = "  [review]" if e["needs_review"] else ""
        print(f"  -{e['amount']:>9,.2f}  {e['label'][:44]}{flag}")
    print()
    print(f"income         {facts['income']:>10,.2f}")
    print(f"position       {facts['position_change']:>10,.2f}")
    print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
