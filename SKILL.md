---
name: TB-Generator
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

### Use the reference examples

Before building, open the example Trial Balances in this skill's `references/` folder and model the output on them. List the folder each run, as examples may be added over time, and use whichever best matches the chosen format and the type of entity.

Currently available:

- `references/Example_TrialBalance_SingleColumn.xlsx`: a single-column TB (Debit positive, Credit negative) built from a set of annual accounts.

Use the examples as a guide to:

- **Layout**: header rows (entity, "Trial Balance", period end, currency/units), then the columns `Account`, `Type`, `Balance`, and a closing `Total` row that is 0.
- **Account order**: assets first, then liabilities, equity, revenue and expenses.
- **Granularity**: split headline lines into detailed accounts as the example does (for instance inventories into raw materials, work in progress, finished goods and goods in transit, and fixed assets into separate cost and accumulated depreciation accounts).
- **Naming**: short, plain account names, with a `- at cost` / `- accumulated depreciation` style suffix for contra accounts.
- **Equity and P&L**: opening retained earnings shown as its own account with the P&L accounts listed individually, not rolled into retained earnings.
- **Rounding**: a visible `Rounding difference` account where the source accounts do not foot.

Do not copy the example's account names or figures. They are only a model for structure and level of detail. Every figure in the new TB must come from the PDF. If no example exists for the chosen format (for example two columns), follow the closest example and let the script produce the Debit/Credit layout.

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

Use an `.xlsx` or `.csv` output name. Write the file to the outputs folder (`/mnt/user-data/outputs/`, for example `/mnt/user-data/outputs/TrialBalance.xlsx`) so it can be offered as a download card in Step 6. **Never write the deliverable to a scratchpad, temp or session working folder.** Files there cannot be turned into a download card. Scratch folders are fine only for the intermediate `input.json`. Name it after the entity and period where known (e.g. `ExampleLtd_TrialBalance_2025-12-31.xlsx`).

The script checks that:

1. Debits equal credits (the single column sums to zero).
2. Profit, total assets, total liabilities and total equity agree to the reported figures.

**If it prints `CHECK FAILED`, no file is written.** Read the differences, find the cause (a missed line, a wrong sign, a wrong type, a contra account) and fix the JSON. Re-run until it passes. If the cause is a genuine rounding difference in the source accounts, add an account named `Rounding difference` so it is visible. Never plug a difference silently, and never change a reported figure to make the check pass.

## Step 6: Output

Once the script passes:

1. Show the Trial Balance in the chat in the format chosen in Step 2, with a header (entity, period end, currency, units) and a totals row.
2. **Always present the file as a download card.** Call the file presentation tool (`present_files`) on the file the script wrote in the outputs folder, so the user gets a downloadable card. Do this on every run that passes the check, even if the table is already shown in the chat. Do not only mention the file path or paste a link.
3. If the user asks for a CSV as well, re-run the script with a `.csv` output name and present that file as a second download card.
4. The download card is the only delivery method. Do not hand over a scratchpad or session-folder path as a substitute. If the card cannot be produced, say so plainly and ask the user how to proceed. Never imply a download is available when it is not.

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
