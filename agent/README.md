# Arus — statement reader and Telegram agent

The optional statement-reader and Telegram delivery module now included in the
same repository as the Arus dashboard and Gmail/OpenRouter ingestion service.

## What it does

    encrypted PDF  ->  reader  ->  Google Sheet  ->  reconciler  ->  card  ->  Telegram

It identifies card repayments, own-account transfers, investments, and refunds
so deterministic reporting does not count the same money twice.

## Files

| File | Job |
| --- | --- |
| `parse_maybank.py` | Reads the Maybank savings layout: trailing signs, running balance, multi-line counterparties |
| `parse_statement.py` | Reads the credit card layout |
| `consolidate.py` | Works out what is really spending. All arithmetic lives here |
| `sorter.py` | Model-based merchant categorisation, with corrections that persist |
| `send_report.py` | Reads the sheet, draws the card, sends it |
| `ask_bot.py` | Answers follow-up questions in the Telegram thread |
| `report_card.html` | The card design. Placeholders only, no logic |

## Design rule

Every figure is computed in deterministic Python before any model sees it.
The model sorts merchants and writes sentences; it never does arithmetic.

## Verification

The reader was tested against a real 7-page Maybank statement and reproduced
its stated totals exactly (RM 6,015.92 out, RM 9,762.18 in), with all 66 rows
agreeing with the running balance column.

## Setup

    # Put real OpenRouter, Google Sheets, and Telegram credentials in agent/.env
    python find_chat_id.py    # after messaging your bot once
    python send_report.py     # build and send
    python ask_bot.py         # listen for questions

No statement, ledger, API key, OAuth token, or generated report is committed.
`.env` and runtime output files must stay ignored.
