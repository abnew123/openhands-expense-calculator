"""Pytest configuration and fixtures for expense tracker tests."""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db import DatabaseManager
from app.models import Transaction
from app.csv_parser import CSVParser


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    db = DatabaseManager(db_path)
    yield db
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def sample_transactions():
    """Create sample transactions for testing."""
    return [
        Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="STARBUCKS STORE #12345",
            category="Food & Drink",
            transaction_type="Sale",
            amount=-4.75,
            memo=""
        ),
        Transaction(
            transaction_date=datetime(2024, 1, 16),
            post_date=datetime(2024, 1, 17),
            description="AMAZON.COM AMZN.COM/BILL",
            category="Shopping",
            transaction_type="Sale",
            amount=-29.99,
            memo=""
        ),
        Transaction(
            transaction_date=datetime(2024, 1, 17),
            post_date=datetime(2024, 1, 18),
            description="PAYMENT THANK YOU - WEB",
            category="Payment",
            transaction_type="Payment",
            amount=150.00,
            memo=""
        ),
        Transaction(
            transaction_date=datetime(2024, 1, 18),
            post_date=datetime(2024, 1, 19),
            description="UBER EATS",
            category="Food & Drink",
            transaction_type="Sale",
            amount=-12.50,
            memo=""
        ),
        Transaction(
            transaction_date=datetime(2024, 1, 20),
            post_date=datetime(2024, 1, 21),
            description="TARGET STORE T-1234",
            category="Shopping",
            transaction_type="Sale",
            amount=-45.67,
            memo=""
        )
    ]


@pytest.fixture
def sample_csv_content():
    """Create sample CSV content for testing."""
    return """Transaction Date,Post Date,Description,Category,Type,Amount,Memo
01/15/2024,01/16/2024,STARBUCKS STORE #12345,Food & Drink,Sale,-4.75,
01/16/2024,01/17/2024,AMAZON.COM AMZN.COM/BILL,Shopping,Sale,-29.99,
01/17/2024,01/18/2024,PAYMENT THANK YOU - WEB,Payment,Payment,150.00,
01/18/2024,01/19/2024,UBER EATS,Food & Drink,Sale,-12.50,
01/20/2024,01/21/2024,TARGET STORE T-1234,Shopping,Sale,-45.67,"""


@pytest.fixture
def invalid_csv_content():
    """Create invalid CSV content for testing."""
    return """Date,Description,Amount
01/15/2024,STARBUCKS,-4.75
01/16/2024,AMAZON,-29.99"""


@pytest.fixture
def csv_parser():
    """Create a CSV parser instance."""
    return CSVParser()