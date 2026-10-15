# SheetFlow

Combine recurring sales CSV files into a clean, Excel-compatible dataset and a readable monthly report.

## What is this project used for?

A small wholesaler receives separate sales files each month. Copying them by hand can duplicate orders and mix invalid dates or quantities into revenue totals. SheetFlow merges these files, validates each record, separates duplicate/conflicting IDs and invalid rows for human review, and creates a monthly summary. Source files are never changed.

## Try it

Requires Python 3.10 or later. No external packages or account needed.

```bash
python sheetflow.py
python -m unittest -v
```

Open `output/report.html` in your browser. Open `output/clean_sales.csv` and `output/monthly_summary.csv` in Excel. UTF-8 BOM helps Excel recognize text. CSV files do not contain native Excel sheets, charts or formulas.

For your own files:

```bash
python sheetflow.py --input path/to/csv_files --output path/to/results
```

Required columns: `order_id,date,product,quantity,unit_price`. Dates use YYYY-MM-DD. Quantity must be a positive integer and price nonnegative with no more than two decimal places. Sample currency is INR. The input folder must contain only intended input CSVs; the output folder must be outside it.

## Working sample

The three included fictional sales files contain 32 input rows. The run produces 24 clean orders, four duplicate/conflicting rows and four invalid rows. All 32 rows reconcile to those outcomes. See `output/quality_report.json` for the actual revenue and row counts, and `output/report.html` for the report.

- `clean_sales.csv`: accepted orders, calculated amounts and source file/line.
- `duplicates.csv`: duplicate or conflicting IDs, retained separately. First valid row wins in alphabetical file/row order. Conflicts require review.
- `rejected_rows.csv`: invalid rows plus reasons and source locations.
- `monthly_summary.csv`: accepted orders, units and revenue by month.
- `quality_report.json`: row reconciliation and total revenue.

Money uses decimal arithmetic. CSV text is escaped against formula injection and HTML output is escaped. Six automated tests check reconciliation, duplicate handling, exact money, injection protection, repeatability, source preservation and input failure conditions.

## Scope and limitations

Self-created portfolio project with fictional sample data, not paid client work. The tool processes local CSV files only. It does not read XLSX, connect to live systems, schedule jobs or send email. Revenue is gross quantity × price, not profit, tax reporting or accounting advice. It assumes one row per order ID; line-item datasets require another key. Performance on large files has not been benchmarked. Never place client-private data in this public repository.
