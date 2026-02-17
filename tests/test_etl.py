import unittest
from data_ingestion.etl_pipeline import extract_data, transform_data

class TestETL(unittest.TestCase):
    def test_extract_data(self):
        df = extract_data('data_ingestion/sample_data.csv')
        self.assertFalse(df.empty)
        self.assertIn('supplier_name', df.columns)

    def test_transform_data(self):
        df = pd.DataFrame({'date': ['2023-01-01'], 'rating': [None]})
        transformed = transform_data(df)
        self.assertEqual(transformed['rating'].iloc[0], 3.0)

if __name__ == '__main__':
    unittest.main()