import csv
import tempfile
import unittest
from pathlib import Path
from sheetflow import run, safe


class SheetFlowTests(unittest.TestCase):
    def test_sample_reconciliation_and_exact_money(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(Path(__file__).parent / 'input', tmp)
            self.assertEqual((result['input_rows'],result['clean_rows'],result['duplicates'],result['rejected_rows']), (32,24,4,4))
            self.assertTrue(result['reconciled'])
            with (Path(tmp)/'clean_sales.csv').open(encoding='utf-8-sig') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(result['revenue_inr'], '51950.00')
            self.assertEqual(len({r['order_id'] for r in rows}),24)
            self.assertEqual(rows[0]['amount'],'1300.00')
            self.assertEqual(rows[0]['product'],'Cotton shirt')

    def test_formula_injection_protection(self):
        self.assertEqual(safe('=HYPERLINK("bad")'), '\'=HYPERLINK("bad")')
        self.assertEqual(safe(' @SUM(1)'), "' @SUM(1)")

    def test_missing_headers_fail_without_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'in').mkdir()
            (root/'in'/'bad.csv').write_text('name\na\n')
            with self.assertRaisesRegex(ValueError,'required headers'):
                run(root/'in',root/'out')
            self.assertFalse((root/'out').exists())

    def test_empty_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'No input'):
                run(tmp,Path(tmp).parent/'unused-output')

    def test_source_preserved_and_repeatable(self):
        source=Path(__file__).parent/'input'
        before={p.name:p.read_bytes() for p in source.glob('*.csv')}
        with tempfile.TemporaryDirectory() as tmp:
            one=run(source,tmp); first=(Path(tmp)/'clean_sales.csv').read_bytes()
            self.assertEqual(run(source,tmp),one)
            self.assertEqual((Path(tmp)/'clean_sales.csv').read_bytes(),first)
        self.assertEqual(before,{p.name:p.read_bytes() for p in source.glob('*.csv')})

    def test_output_inside_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'outside'):
                run(tmp,Path(tmp)/'output')

if __name__ == '__main__':
    unittest.main()
