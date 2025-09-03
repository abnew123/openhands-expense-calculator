"""Tests for database operations."""

import pytest
from datetime import datetime

from app.models import Transaction


class TestDatabaseManager:
    """Test database manager functionality."""
    
    def test_database_initialization(self, temp_db):
        """Test database initialization creates tables."""
        # Database should be initialized and ready
        assert temp_db is not None
        
        # Test that we can get an empty transaction count
        count = temp_db.get_transaction_count()
        assert count == 0
    
    def test_insert_single_transaction(self, temp_db, sample_transactions):
        """Test inserting a single transaction."""
        transaction = sample_transactions[0]
        
        transaction_id = temp_db.insert_transaction(transaction)
        assert transaction_id is not None
        assert transaction_id > 0
        
        # Verify transaction count
        count = temp_db.get_transaction_count()
        assert count == 1
    
    def test_insert_transactions_batch(self, temp_db, sample_transactions):
        """Test inserting multiple transactions in batch."""
        transaction_ids = temp_db.insert_transactions_batch(sample_transactions)
        
        assert len(transaction_ids) == len(sample_transactions)
        assert all(tid > 0 for tid in transaction_ids)
        
        # Verify transaction count
        count = temp_db.get_transaction_count()
        assert count == len(sample_transactions)
    
    def test_get_all_transactions(self, temp_db, sample_transactions):
        """Test retrieving all transactions."""
        # Insert sample transactions
        temp_db.insert_transactions_batch(sample_transactions)
        
        # Retrieve all transactions
        retrieved_transactions = temp_db.get_all_transactions()
        
        assert len(retrieved_transactions) == len(sample_transactions)
        
        # Verify first transaction (should be sorted by date DESC)
        first_retrieved = retrieved_transactions[0]
        assert first_retrieved.description == "TARGET STORE T-1234"  # Latest date
    
    def test_get_transactions_by_date_range(self, temp_db, sample_transactions):
        """Test retrieving transactions by date range."""
        # Insert sample transactions
        temp_db.insert_transactions_batch(sample_transactions)
        
        # Get transactions for a specific date range
        start_date = datetime(2024, 1, 16)
        end_date = datetime(2024, 1, 18)
        
        filtered_transactions = temp_db.get_transactions_by_date_range(start_date, end_date)
        
        # Should get 3 transactions (1/16, 1/17, 1/18)
        assert len(filtered_transactions) == 3
        
        # Verify all transactions are within range
        for transaction in filtered_transactions:
            assert start_date <= transaction.transaction_date <= end_date
    
    def test_get_transactions_by_category(self, temp_db, sample_transactions):
        """Test retrieving transactions by category."""
        # Insert sample transactions
        temp_db.insert_transactions_batch(sample_transactions)
        
        # Get transactions for "Food & Drink" category
        food_transactions = temp_db.get_transactions_by_category("Food & Drink")
        
        # Should get 2 transactions (Starbucks and Uber Eats)
        assert len(food_transactions) == 2
        
        # Verify all transactions have correct category
        for transaction in food_transactions:
            assert transaction.category == "Food & Drink"
    
    def test_update_transaction_category(self, temp_db, sample_transactions):
        """Test updating transaction category."""
        # Insert sample transactions
        transaction_ids = temp_db.insert_transactions_batch(sample_transactions)
        
        # Update first transaction's category
        first_id = transaction_ids[0]
        success = temp_db.update_transaction_category(first_id, "Updated Category")
        
        assert success is True
        
        # Verify the update
        all_transactions = temp_db.get_all_transactions()
        updated_transaction = next(t for t in all_transactions if t.id == first_id)
        assert updated_transaction.category == "Updated Category"
    
    def test_update_nonexistent_transaction_category(self, temp_db):
        """Test updating category for non-existent transaction."""
        success = temp_db.update_transaction_category(999, "New Category")
        assert success is False
    
    def test_delete_transaction(self, temp_db, sample_transactions):
        """Test deleting a transaction."""
        # Insert sample transactions
        transaction_ids = temp_db.insert_transactions_batch(sample_transactions)
        
        # Delete first transaction
        first_id = transaction_ids[0]
        success = temp_db.delete_transaction(first_id)
        
        assert success is True
        
        # Verify transaction count decreased
        count = temp_db.get_transaction_count()
        assert count == len(sample_transactions) - 1
    
    def test_delete_nonexistent_transaction(self, temp_db):
        """Test deleting non-existent transaction."""
        success = temp_db.delete_transaction(999)
        assert success is False
    
    def test_get_categories(self, temp_db, sample_transactions):
        """Test retrieving unique categories."""
        # Insert sample transactions
        temp_db.insert_transactions_batch(sample_transactions)
        
        categories = temp_db.get_categories()
        
        expected_categories = {"Food & Drink", "Shopping", "Payment"}
        assert set(categories) == expected_categories
    
    def test_transaction_exists(self, temp_db, sample_transactions):
        """Test checking if transaction exists (duplicate detection)."""
        transaction = sample_transactions[0]
        
        # Transaction should not exist initially
        assert temp_db.transaction_exists(transaction) is False
        
        # Insert transaction
        temp_db.insert_transaction(transaction)
        
        # Transaction should now exist
        assert temp_db.transaction_exists(transaction) is True
    
    def test_rename_category(self, temp_db, sample_transactions):
        """Test renaming a category across all transactions."""
        # Insert sample transactions
        temp_db.insert_transactions_batch(sample_transactions)
        
        # Rename "Food & Drink" to "Food"
        updated_count = temp_db.rename_category("Food & Drink", "Food")
        
        assert updated_count == 2  # Should update 2 transactions
        
        # Verify the rename
        categories = temp_db.get_categories()
        assert "Food" in categories
        assert "Food & Drink" not in categories
        
        # Verify transactions were updated
        food_transactions = temp_db.get_transactions_by_category("Food")
        assert len(food_transactions) == 2
    
    def test_merge_categories(self, temp_db, sample_transactions):
        """Test merging multiple categories."""
        # Insert sample transactions
        temp_db.insert_transactions_batch(sample_transactions)
        
        # Merge "Food & Drink" and "Shopping" into "General"
        categories_to_merge = ["Food & Drink", "Shopping"]
        updated_count = temp_db.merge_categories(categories_to_merge, "General")
        
        assert updated_count == 4  # Should update 4 transactions (2 food + 2 shopping)
        
        # Verify the merge
        categories = temp_db.get_categories()
        assert "General" in categories
        assert "Food & Drink" not in categories
        assert "Shopping" not in categories
        
        # Verify transactions were updated
        general_transactions = temp_db.get_transactions_by_category("General")
        assert len(general_transactions) == 4
    
    def test_delete_category(self, temp_db, sample_transactions):
        """Test deleting a category with replacement."""
        # Insert sample transactions
        temp_db.insert_transactions_batch(sample_transactions)
        
        # Delete "Food & Drink" category, replace with "Uncategorized"
        updated_count = temp_db.delete_category("Food & Drink", "Uncategorized")
        
        assert updated_count == 2  # Should update 2 transactions
        
        # Verify the deletion
        categories = temp_db.get_categories()
        assert "Food & Drink" not in categories
        assert "Uncategorized" in categories
        
        # Verify transactions were updated
        uncategorized_transactions = temp_db.get_transactions_by_category("Uncategorized")
        assert len(uncategorized_transactions) == 2
    
    def test_get_category_stats(self, temp_db, sample_transactions):
        """Test getting category statistics."""
        # Insert sample transactions
        temp_db.insert_transactions_batch(sample_transactions)
        
        stats = temp_db.get_category_stats()
        
        # Should have stats for 3 categories
        assert len(stats) == 3
        assert "Food & Drink" in stats
        assert "Shopping" in stats
        assert "Payment" in stats
        
        # Check Food & Drink stats
        food_stats = stats["Food & Drink"]
        assert food_stats['transaction_count'] == 2
        assert food_stats['total_expenses'] == 17.25  # 4.75 + 12.50
        assert food_stats['total_income'] == 0
        assert food_stats['net_amount'] == -17.25
        
        # Check Payment stats
        payment_stats = stats["Payment"]
        assert payment_stats['transaction_count'] == 1
        assert payment_stats['total_expenses'] == 0
        assert payment_stats['total_income'] == 150.0
        assert payment_stats['net_amount'] == 150.0
    
    def test_empty_database_operations(self, temp_db):
        """Test operations on empty database."""
        # Test getting transactions from empty database
        transactions = temp_db.get_all_transactions()
        assert len(transactions) == 0
        
        # Test getting categories from empty database
        categories = temp_db.get_categories()
        assert len(categories) == 0
        
        # Test getting stats from empty database
        stats = temp_db.get_category_stats()
        assert len(stats) == 0
        
        # Test transaction count
        count = temp_db.get_transaction_count()
        assert count == 0