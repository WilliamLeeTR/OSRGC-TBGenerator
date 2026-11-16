---
name: tb-generator
description: Reverse engineers a Trial Balance from an annual accounts PDF. Use when the user wants a Trial Balance built from financial statements, as one signed column or Debit/Credit columns.
---

# Trial Balance Generator

Reads a PDF of annual accounts and reverse engineers the Trial Balance that would have produced those accounts.

## Step 1: Request the input

Ask the user to upload the PDF report (annual accounts / financial report) to the conversation if they have not already. Do not proceed until a PDF is supplied.

If the file is not a PDF, or does not appear to be annual accounts / financial statements, tell the user and ask for the correct document.

## Step 2: Ask for the output format

Before producing anything, ask the user which layout they want:

1. **Single column**: one balance column, where **Debit balances are positive** and **Credit balances are negative**.
2. **Two columns**: one **Debit** column and one **Credit** column, with each balance shown as a positive number in its column.

Wait for the answer. Do not assume a default.

## Step 3: Read the accounts

Extract from the PDF, for the current year (and the comparative year if present):

- Income statement / profit and loss (revenue, cost of sales, expenses, finance items, tax)
- Balance sheet (non-current and current assets, liabilities, equity)
- Relevant notes that break down headline figures (e.g. fixed assets, debtors, creditors, provisions, reserves)
- Cash flow statement and statement of changes in equity where they help to split balances

Record the reporting currency, units (e.g. thousands or millions) and period end date.

## Step 4: Build the Trial Balance

Convert each line into a Trial Balance account:

- **Debit-nature accounts**: assets, expenses and losses.
- **Credit-nature accounts**: liabilities, equity, revenue and gains.
- Contra accounts (accumulated depreciation, provisions, treasury shares, dividends) carry the opposite sign to their parent.
- Use note breakdowns to create detailed accounts where available. Otherwise use the line as presented.
- Use a closing Trial Balance that includes the profit and loss accounts. Do not roll the result into retained earnings.
- Dividends, movements in reserves and other equity items should appear as separate accounts where the statement of changes in equity shows them.

## Step 5: Validate with the script

Do not add up the Trial Balance by hand. Write the accounts to a JSON file and run the bundled script, which does the check:

```json
{
  "entity": "Example Ltd",
  "period_end": "31 December 2025",
  "currency": "GBP",
  "units": "thousands",
  "format": "single",
  "accounts": [
    {"account": "Trade receivables", "type": "asset", "balance": 1200},
    {"account": "Trade payables", "type": "liability", "balance": -800}
  ],
  "reported": {"profit": 150, "total_assets": 5000, "total_liabilities": 2000, "total_equity": 3000}
}
```

- `format` is `single` or `two_column`, as chosen in Step 2.
- `balance` is always **Debit positive, Credit negative** in the JSON, whichever format the user chose. The script converts it for the output.
- `type` is one of `asset`, `liability`, `equity`, `revenue`, `expense`.
- `reported` holds the figures printed in the accounts (profit for the year, total assets, total liabilities, total equity). Include every one the PDF states.

Run it from this skill's folder:

```
python scripts/build_tb.py input.json TrialBalance.xlsx
```

Use an `.xlsx` or `.csv` output name.

The script checks that:

1. Debits equal credits (the single column sums to zero).
2. Profit, total assets, total liabilities and total equity agree to the reported figures.

**If it prints `CHECK FAILED`, no file is written.** Read the differences, find the cause (a missed line, a wrong sign, a wrong type, a contra account) and fix the JSON. Re-run until it passes. If the cause is a genuine rounding difference in the source accounts, add an account named `Rounding difference` so it is visible. Never plug a difference silently, and never change a reported figure to make the check pass.

## Step 6: Output

Once the script passes:

1. Show the Trial Balance in the chat in the format chosen in Step 2, with a header (entity, period end, currency, units) and a totals row.
2. Provide the .xlsx file the script wrote as a download. Offer a CSV as well if wanted.

**Single column**

| Account | Balance |
|---|---|
| Trade receivables | 1,200 |
| Trade payables | (800) |

**Two columns**

| Account | Debit | Credit |
|---|---|---|
| Trade receivables | 1,200 | |
| Trade payables | | 800 |

## Notes

- State any assumptions made, including where you split or inferred an account that the accounts do not show separately.
- A Trial Balance rebuilt from published accounts is an estimate. It cannot reproduce the detailed ledger accounts or any transactions netted off in the published figures. Tell the user this.
- Never invent figures that are not in or derivable from the PDF.
