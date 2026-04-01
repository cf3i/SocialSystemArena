
import unittest
from src.datautils import __init__ # Import to ensure the package is recognized

class TestDataUtils(unittest.TestCase):
    def test_placeholder(self):
        self.assertTrue(True, "Placeholder test passed")

if __name__ == '__main__':
    unittest.main()
