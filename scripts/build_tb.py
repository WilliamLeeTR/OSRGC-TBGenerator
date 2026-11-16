#!/usr/bin/env python3
"""Validate a reverse-engineered Trial Balance and write it to .xlsx or .csv.

Usage:
    python build_tb.py input.json output.xlsx
    python build_tb.py input.json output.csv

Input JSON:
{
  "entity": "Example Ltd",
  "period_end": "31 December 2025",
  "currency": "GBP",
  "units": "thousands",
  "format": "single" | "two_column",
  "accounts": [
    {"account": "Trade receivables", "type": "asset",     "balance": 1200},
    {"account": "Trade payables",    "type": "liability", "balance": -800}
  ],
  "reported": {                       # optional; each key is checked if present
    "profit": 150, "total_assets": 5000,
    "total_liabilities": 2000, "total_equity": 3000
  }
}

Sign convention for "balance": Debit positive, Credit negative.
"type" is one of: asset, liability, equity, revenue, expense.
Closing TB: revenue and expense accounts are included, so current-year profit
is NOT inside the equity accounts.

Checks (all must pass or no file is written, exit code 1):
  1. All balances sum to zero (debits == credits).
  2. Any "reported" figure supplied agrees with the TB.
Rounding differences must be added by the caller as an explicit account named
"Rounding difference"; this script never plugs a difference.
"""
import csv
import json
import sys
from decimal import Decimal, ROUND_HALF_UP

TYPES = {"asset", "liability", "equity", "revenue", "expense"}
ORDER = ["asset", "liability", "equity", "revenue", "expense"]
TOLERANCE = Decimal("0.5")  # in the units of the accounts, for reported-figure checks


def d(value):
    return Decimal(str(value))


def load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    fmt = data.get("format")
    if fmt not in ("single", "two_column"):
        raise ValueError('"format" must be "single" or "two_column"')
    accounts = data.get("accounts") or []
    if not accounts:
        raise ValueError('"accounts" is empty')
    for a in accounts:
        if not a.get("account"):
            raise ValueError(f"account without a name: {a}")
        if a.get("type") not in TYPES:
            raise ValueError(f'{a.get("account")}: "type" must be one of {sorted(TYPES)}')
        a["balance"] = d(a["balance"])
    return data


def totals(accounts):
    by = {t: Decimal(0) for t in TYPES}
    for a in accounts:
        by[a["type"]] += a["balance"]
    debit = sum((a["balance"] for a in accounts if a["balance"] > 0), Decimal(0))
    credit = -sum((a["balance"] for a in accounts if a["balance"] < 0), Decimal(0))
    profit = -(by["revenue"] + by["expense"])
    return {
        "debit": debit,
        "credit": credit,
        "net": debit - credit,
        "profit": profit,
        "total_assets": by["asset"],
        "total_liabilities": -by["liability"],
        "total_equity": -by["equity"] + profit,
    }


def check(data, t):
    problems = []
    if t["net"] != 0:
        problems.append(
            f"Trial Balance does not balance: debits {t['debit']:,} vs credits "
            f"{t['credit']:,} (difference {t['net']:,}). Find the cause; do not plug it."
        )
    for key, label in [
        ("profit", "Profit for the year"),
        ("total_assets", "Total assets"),
        ("total_liabilities", "Total liabilities"),
        ("total_equity", "Total equity"),
    ]:
        rep = (data.get("reported") or {}).get(key)
        if rep is None:
            continue
        diff = t[key] - d(rep)
        if abs(diff) > TOLERANCE:
            problems.append(
                f"{label}: TB gives {t[key]:,} but accounts report {d(rep):,} "
                f"(difference {diff:,})."
            )
    return problems


def sorted_accounts(accounts):
    return sorted(accounts, key=lambda a: ORDER.index(a["type"]))  # stable within type


def header_lines(data):
    return [
        data.get("entity", ""),
        "Trial Balance",
        f"Period end: {data.get('period_end', '')}",
        f"Currency: {data.get('currency', '')}"
        + (f" ({data['units']})" if data.get("units") else ""),
    ]


def rows(data, t):
    """Return (column_headers, body_rows, totals_row)."""
    accts = sorted_accounts(data["accounts"])
    if data["format"] == "single":
        head = ["Account", "Type", "Balance"]
        body = [[a["account"], a["type"], a["balance"]] for a in accts]
        tot = ["Total", "", t["net"]]
    else:
        head = ["Account", "Type", "Debit", "Credit"]
        body = [
            [
                a["account"],
                a["type"],
                a["balance"] if a["balance"] > 0 else None,
                -a["balance"] if a["balance"] < 0 else None,
            ]
            for a in accts
        ]
        tot = ["Total", "", t["debit"], t["credit"]]
    return head, body, tot


def write_csv(path, data, t):
    head, body, tot = rows(data, t)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        for line in header_lines(data):
            w.writerow([line])
        w.writerow([])
        w.writerow(head)
        for r in body + [tot]:
            w.writerow(["" if v is None else v for v in r])


def write_xlsx(path, data, t):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side

    head, body, tot = rows(data, t)
    wb = Workbook()
    ws = wb.active
    ws.title = "Trial Balance"
    for i, line in enumerate(header_lines(data), start=1):
        ws.cell(row=i, column=1, value=line).font = Font(bold=True, size=14 if i == 2 else 11)
    start = len(header_lines(data)) + 2
    for c, h in enumerate(head, start=1):
        cell = ws.cell(row=start, column=c, value=h)
        cell.font = Font(bold=True)
        cell.border = Border(bottom=Side(style="thin"))
        if c > 2:
            cell.alignment = Alignment(horizontal="right")
    num_fmt = "#,##0;(#,##0);-"  # negatives in brackets, zero as dash
    for r, row in enumerate(body + [tot], start=start + 1):
        for c, v in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=float(v) if isinstance(v, Decimal) else v)
            if c > 2:
                cell.number_format = num_fmt
    last = start + len(body) + 1
    for c in range(1, len(head) + 1):
        cell = ws.cell(row=last, column=c)
        cell.font = Font(bold=True)
        cell.border = Border(top=Side(style="thin"), bottom=Side(style="double"))
    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 12
    for col in "CD":
        ws.column_dimensions[col].width = 16
    ws.freeze_panes = ws.cell(row=start + 1, column=1)
    wb.save(path)


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    src, dst = argv[1], argv[2]
    try:
        data = load(src)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"INPUT ERROR: {e}")
        return 2
    t = totals(data["accounts"])
    problems = check(data, t)
    print(f"Debits:  {t['debit']:,}")
    print(f"Credits: {t['credit']:,}")
    print(f"Profit for the year: {t['profit']:,}")
    print(f"Total assets: {t['total_assets']:,}  liabilities: {t['total_liabilities']:,}  equity: {t['total_equity']:,}")
    if problems:
        print("\nCHECK FAILED - no file written:")
        for p in problems:
            print(f"  - {p}")
        return 1
    if dst.lower().endswith(".csv"):
        write_csv(dst, data, t)
    elif dst.lower().endswith(".xlsx"):
        write_xlsx(dst, data, t)
    else:
        print("OUTPUT ERROR: output file must end in .xlsx or .csv")
        return 2
    print(f"\nAll checks passed. Written: {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
