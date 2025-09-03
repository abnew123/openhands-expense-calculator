"""Tests for data models."""

import pytest
from datetime import datetime
from decimal import Decimal

from app.models import Transaction


class TestTransaction:
    """Test Transaction model."""
    
    def test_transaction_creation(self):
        """Test creating a valid transaction."""
        transaction = Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="STARBUCKS STORE #12345",
            category="Food & Drink",
            transaction_type="Sale",
            amount=-4.75,
            memo=""
        )
        
        assert transaction.transaction_date == datetime(2024, 1, 15)
        assert transaction.post_date == datetime(2024, 1, 16)
        assert transaction.description == "STARBUCKS STORE #12345"
        assert transaction.category == "Food & Drink"
        assert transaction.transaction_type == "Sale"
        assert transaction.amount == Decimal('-4.75')
        assert transaction.memo == ""
    
    def test_transaction_is_expense(self):
        """Test is_expense method."""
        expense = Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="STARBUCKS",
            category="Food",
            transaction_type="Sale",
            amount=-4.75,
            memo=""
        )
        
        payment = Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="PAYMENT",
            category="Payment",
            transaction_type="Payment",
            amount=150.00,
            memo=""
        )
        
        assert expense.is_expense() is True
        assert payment.is_expense() is False
    
    def test_transaction_is_payment(self):
        """Test is_payment method."""
        expense = Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="STARBUCKS",
            category="Food",
            transaction_type="Sale",
            amount=-4.75,
            memo=""
        )
        
        payment = Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="PAYMENT",
            category="Payment",
            transaction_type="Payment",
            amount=150.00,
            memo=""
        )
        
        assert expense.is_payment() is False
        assert payment.is_payment() is True
    
    def test_transaction_to_dict(self):
        """Test to_dict method."""
        transaction = Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="STARBUCKS",
            category="Food",
            transaction_type="Sale",
            amount=-4.75,
            memo="Test memo"
        )
        
        result = transaction.to_dict()
        
        assert result['transaction_date'] == '2024-01-15T00:00:00'
        assert result['post_date'] == '2024-01-16T00:00:00'
        assert result['description'] == 'STARBUCKS'
        assert result['category'] == 'Food'
        assert result['transaction_type'] == 'Sale'
        assert result['amount'] == -4.75
        assert result['memo'] == 'Test memo'
    
    def test_transaction_from_dict(self):
        """Test from_dict class method."""
        data = {
            'id': 1,
            'transaction_date': '2024-01-15T00:00:00',
            'post_date': '2024-01-16T00:00:00',
            'description': 'STARBUCKS',
            'category': 'Food',
            'transaction_type': 'Sale',
            'amount': -4.75,
            'memo': 'Test memo'
        }
        
        transaction = Transaction.from_dict(data)
        
        assert transaction.id == 1
        assert transaction.transaction_date == datetime(2024, 1, 15)
        assert transaction.post_date == datetime(2024, 1, 16)
        assert transaction.description == 'STARBUCKS'
        assert transaction.category == 'Food'
        assert transaction.transaction_type == 'Sale'
        assert transaction.amount == Decimal('-4.75')
        assert transaction.memo == 'Test memo'
    
    def test_transaction_validation(self):
        """Test transaction validation."""
        # Test with empty description
        with pytest.raises(ValueError):
            Transaction(
                transaction_date=datetime(2024, 1, 15),
                post_date=datetime(2024, 1, 16),
                description="",
                category="Food",
                transaction_type="Sale",
                amount=-4.75,
                memo=""
            )
        
        # Test with empty category (should default to "Uncategorized")
        transaction = Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="STARBUCKS",
            category="",
            transaction_type="Sale",
            amount=-4.75,
            memo=""
        )
        assert transaction.category == "Uncategorized"
        
        # Test with zero amount
        with pytest.raises(ValueError):
            Transaction(
                transaction_date=datetime(2024, 1, 15),
                post_date=datetime(2024, 1, 16),
                description="STARBUCKS",
                category="Food",
                transaction_type="Sale",
                amount=0,
                memo=""
            )
    
    def test_transaction_equality(self):
        """Test transaction equality comparison."""
        transaction1 = Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="STARBUCKS",
            category="Food",
            transaction_type="Sale",
            amount=-4.75,
            memo=""
        )
        
        transaction2 = Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="STARBUCKS",
            category="Food",
            transaction_type="Sale",
            amount=-4.75,
            memo=""
        )
        
        transaction3 = Transaction(
            transaction_date=datetime(2024, 1, 15),
            post_date=datetime(2024, 1, 16),
            description="AMAZON",
            category="Shopping",
            transaction_type="Sale",
            amount=-29.99,
            memo=""
        )
        
        assert transaction1 == transaction2
        assert transaction1 != transaction3