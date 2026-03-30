"""Tests for datautils package"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_hello():
    """Test hello function"""
    from datautils import hello
    assert hello() == "Hello from datautils"

if __name__ == "__main__":
    test_hello()
    print("All tests passed!")
