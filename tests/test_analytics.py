import unittest
from analytics.supplier_scoring import score_suppliers
import pandas as pd

class TestSupplierScoring(unittest.TestCase):
    def test_score_suppliers(self):
        df = pd.DataFrame({
            'id': [1, 2],
            'name': ['A', 'B'],
            'location': ['USA', 'China'],
            'rating': [4.0, 3.0],
            'avg_spend': [1000, 2000],
            'invoice_count': [10, 5]
        })
        scored = score_suppliers(df)
        self.assertIn('score', scored.columns)
        self.assertGreater(scored['score'].iloc[0], 0)

if __name__ == '__main__':
    unittest.main()