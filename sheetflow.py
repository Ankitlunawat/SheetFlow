"""Merge sales CSV files, validate records and write an auditable report.

Python 3.10+. No third-party dependencies. Monetary arithmetic uses Decimal.
"""
import argparse
import csv
import html
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

FIELDS = ['order_id', 'date', 'product', 'quantity', 'unit_price']


def safe(value):
    """Prevent spreadsheet formula interpretation of untrusted text cells."""
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text


def write_csv(path, fields, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: safe(row.get(k, '')) for k in fields} for row in rows)


def run(input_dir, output_dir):
    input_dir, output_dir = Path(input_dir).resolve(), Path(output_dir).resolve()
    if input_dir == output_dir or input_dir in output_dir.parents:
        raise ValueError('Output must be outside the input directory.')
    files = sorted(input_dir.glob('*.csv'))
    if not files:
        raise ValueError('No input CSV files found.')
    clean, rejected, duplicates, seen = [], [], [], {}
    input_rows = 0
    for file in files:
        with file.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            if not set(FIELDS).issubset(reader.fieldnames or []):
                raise ValueError(f'{file.name}: required headers are {FIELDS}')
            for line, raw in enumerate(reader, 2):
                input_rows += 1
                trace = {'source_file': file.name, 'source_row': line}
                try:
                    row = {k: (raw.get(k) or '').strip() for k in FIELDS}
                    if not row['order_id'] or not row['product']:
                        raise ValueError('Missing order ID or product')
                    row['date'] = date.fromisoformat(row['date']).isoformat()
                    quantity = int(row['quantity'])
                    price = Decimal(row['unit_price'])
                    if quantity <= 0 or not price.is_finite() or price < 0:
                        raise ValueError('Quantity must be positive and price finite/nonnegative')
                    if price != price.quantize(Decimal('.01')):
                        raise ValueError('Price must have at most two decimal places')
                    row.update(quantity=quantity, unit_price=f'{price:.2f}', amount=f'{quantity * price:.2f}')
                except (ValueError, InvalidOperation, OverflowError) as exc:
                    rejected.append({**{k: raw.get(k, '') for k in FIELDS}, **trace, 'reason': str(exc)})
                    continue
                if row['order_id'] in seen:
                    previous = seen[row['order_id']]
                    reason = 'Duplicate order ID' if row == previous else 'Conflicting order ID; first valid row retained'
                    duplicates.append({**row, **trace, 'reason': reason})
                    continue
                seen[row['order_id']] = row.copy()
                clean.append({**row, **trace})
    totals = defaultdict(lambda: {'orders': 0, 'units': 0, 'revenue': Decimal('0')})
    for row in clean:
        month = row['date'][:7]
        totals[month]['orders'] += 1
        totals[month]['units'] += row['quantity']
        totals[month]['revenue'] += Decimal(row['amount'])
    monthly = [{'month': m, **v, 'revenue': f"{v['revenue']:.2f}"} for m, v in sorted(totals.items())]
    quality = {'files': len(files), 'input_rows': input_rows, 'clean_rows': len(clean),
               'duplicates': len(duplicates), 'rejected_rows': len(rejected),
               'reconciled': input_rows == len(clean) + len(duplicates) + len(rejected),
               'revenue_inr': f"{sum((Decimal(r['amount']) for r in clean), Decimal('0')):.2f}"}
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / 'clean_sales.csv', FIELDS + ['amount', 'source_file', 'source_row'], clean)
    write_csv(output_dir / 'duplicates.csv', FIELDS + ['amount', 'source_file', 'source_row', 'reason'], duplicates)
    write_csv(output_dir / 'rejected_rows.csv', FIELDS + ['source_file', 'source_row', 'reason'], rejected)
    write_csv(output_dir / 'monthly_summary.csv', ['month', 'orders', 'units', 'revenue'], monthly)
    (output_dir / 'quality_report.json').write_text(json.dumps(quality, indent=2) + '\n')
    def table(rows, fields):
        return '<table><tr>' + ''.join(f'<th>{html.escape(f)}</th>' for f in fields) + '</tr>' + ''.join('<tr>' + ''.join(f'<td>{html.escape(str(r.get(f, "")))}</td>' for f in fields) + '</tr>' for r in rows) + '</table>'
    report = '''<!doctype html><meta charset="utf-8"><title>SheetFlow results</title>
<style>body{font:18px system-ui;background:#f3f6fa;color:#17263a;margin:50px;max-width:1200px}h1{font-size:42px}table{border-collapse:collapse;background:white;width:100%;margin:20px 0}td,th{padding:12px;text-align:left;border-bottom:1px solid #dce3eb}th{background:#15283e;color:white}.metrics{display:flex;gap:24px;padding:25px;background:#d8f4e9}.metrics b{font-size:30px;display:block}small{color:#52647a}</style>
<small>SELF-CREATED PORTFOLIO PROJECT / FICTIONAL SALES DATA</small><h1>SheetFlow</h1><p>Sales files combined, checked and ready for Excel.</p>'''
    report += '<div class="metrics">' + ''.join(f'<div><b>{quality[k]}</b>{label}</div>' for k, label in [('input_rows','input rows'),('clean_rows','clean orders'),('duplicates','duplicates held'),('rejected_rows','invalid rows held')]) + '</div>'
    report += '<h2>Monthly results (INR)</h2>' + table(monthly, ['month','orders','units','revenue'])
    report += '<h2>Clean delivery preview</h2>' + table(clean[:8], FIELDS + ['amount'])
    report += '<p>Every output row retains its source file and row number. Duplicate and invalid rows are delivered separately for review. No source file is modified.</p>'
    (output_dir / 'report.html').write_text(report, encoding='utf-8')
    return quality


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default=str(Path(__file__).parent / 'input'))
    parser.add_argument('--output', default=str(Path(__file__).parent / 'output'))
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output), indent=2))
