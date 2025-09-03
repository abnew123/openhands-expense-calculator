"""Integration tests for end-to-end workflows."""

import pytest
from datetime import datetime

from app.csv_parser import CSVParser
from app.models import Transaction


class TestIntegration:
    """Test end-to-end integration workflows."""
    
    def test_csv_to_database_workflow(self, temp_db, sample_csv_content):
        """Test complete CSV upload to database workflow."""
        parser = CSVParser()
        
        # Step 1: Validate CSV format
        is_valid = parser.validate_csv_format(sample_csv_content, "chase")
        assert is_valid is True
        
        # Step 2: Parse CSV to transactions
        transactions = parser.parse_chase_csv(sample_csv_content)
        assert len(transactions) == 5
        
        # Step 3: Check for duplicates (should be none initially)
        new_transactions = []
        for transaction in transactions:
            if not temp_db.transaction_exists(transaction):
                new_transactions.append(transaction)
        
        assert len(new_transactions) == 5  # All should be new
        
        # Step 4: Insert transactions into database
        transaction_ids = temp_db.insert_transactions_batch(new_transactions)
        assert len(transaction_ids) == 5
        
        # Step 5: Verify data in database
        all_transactions = temp_db.get_all_transactions()
        assert len(all_transactions) == 5
        
        # Step 6: Test duplicate detection on re-upload
        duplicate_transactions = []
        for transaction in transactions:
            if not temp_db.transaction_exists(transaction):
                duplicate_transactions.append(transaction)
        
        assert len(duplicate_transactions) == 0  # All should be duplicates now
    
    def test_category_management_workflow(self, temp_db, sample_transactions):
        """Test complete category management workflow."""
        # Step 1: Insert sample data
        temp_db.insert_transactions_batch(sample_transactions)
        
        # Step 2: Get initial categories
        initial_categories = temp_db.get_categories()
        assert "Food & Drink" in initial_categories
        assert "Shopping" in initial_categories
        
        # Step 3: Update individual transaction category
        all_transactions = temp_db.get_all_transactions()
        first_transaction = all_transactions[0]
        success = temp_db.update_transaction_category(first_transaction.id, "Updated Category")
        assert success is True
        
        # Step 4: Rename category
        updated_count = temp_db.rename_category("Food & Drink", "Food")
        assert updated_count >= 1  # At least one transaction should be updated
        
        # Step 5: Merge categories
        categories_to_merge = ["Shopping"]
        merge_count = temp_db.merge_categories(categories_to_merge, "General")
        assert merge_count >= 1
        
        # Step 6: Verify final state
        final_categories = temp_db.get_categories()
        assert "Food" in final_categories or "General" in final_categories
        assert "Updated Category" in final_categories
    
    def test_filtering_workflow(self, temp_db, sample_transactions):
        """Test transaction filtering workflow."""
        # Step 1: Insert sample data
        temp_db.insert_transactions_batch(sample_transactions)
        
        # Step 2: Filter by date range
        start_date = datetime(2024, 1, 16)
        end_date = datetime(2024, 1, 18)
        date_filtered = temp_db.get_transactions_by_date_range(start_date, end_date)
        
        # Step 3: Filter by category
        category_filtered = temp_db.get_transactions_by_category("Food & Drink")
        
        # Step 4: Verify filtering results
        assert len(date_filtered) > 0
        assert len(category_filtered) > 0
        
        # All date-filtered transactions should be within range
        for transaction in date_filtered:
            assert start_date <= transaction.transaction_date <= end_date
        
        # All category-filtered transactions should have correct category
        for transaction in category_filtered:
            assert transaction.category == "Food & Drink"
    
    def test_analytics_workflow(self, temp_db, sample_transactions):
        """Test analytics data preparation workflow."""
        # Step 1: Insert sample data
        temp_db.insert_transactions_batch(sample_transactions)
        
        # Step 2: Get category statistics
        stats = temp_db.get_category_stats()
        assert len(stats) > 0
        
        # Step 3: Verify expense vs payment separation
        all_transactions = temp_db.get_all_transactions()
        expenses = [t for t in all_transactions if t.is_expense()]
        payments = [t for t in all_transactions if t.is_payment()]
        
        assert len(expenses) > 0
        assert len(payments) > 0
        assert len(expenses) + len(payments) == len(all_transactions)
        
        # Step 4: Verify category totals
        for category, stat in stats.items():
            category_transactions = temp_db.get_transactions_by_category(category)
            assert stat['transaction_count'] == len(category_transactions)
    
    def test_error_handling_workflow(self, temp_db):
        """Test error handling in various workflows."""
        parser = CSVParser()
        
        # Test invalid CSV handling
        invalid_csv = "invalid,csv,content"
        is_valid = parser.validate_csv_format(invalid_csv, "chase")
        assert is_valid is False
        
        transactions = parser.parse_chase_csv(invalid_csv)
        assert len(transactions) == 0
        
        # Test database operations with invalid data
        success = temp_db.update_transaction_category(999, "Nonexistent")
        assert success is False
        
        success = temp_db.delete_transaction(999)
        assert success is False
        
        # Test operations on empty database
        empty_stats = temp_db.get_category_stats()
        assert len(empty_stats) == 0
        
        empty_categories = temp_db.get_categories()
        assert len(empty_categories) == 0
    
    def test_large_dataset_workflow(self, temp_db):
        """Test workflow with larger dataset."""
        # Create a larger dataset
        large_transactions = []
        for i in range(100):
            transaction = Transaction(
                transaction_date=datetime(2024, 1, 1 + (i % 30)),
                post_date=datetime(2024, 1, 2 + (i % 30)),
                description=f"TRANSACTION {i}",
                category=f"Category {i % 5}",
                transaction_type="Sale",
                amount=-(10.0 + i),
                memo=""
            )
            large_transactions.append(transaction)
        
        # Insert large batch
        transaction_ids = temp_db.insert_transactions_batch(large_transactions)
        assert len(transaction_ids) == 100
        
        # Test retrieval performance
        all_transactions = temp_db.get_all_transactions()
        assert len(all_transactions) == 100
        
        # Test category operations on large dataset
        stats = temp_db.get_category_stats()
        assert len(stats) == 5  # 5 different categories
        
        # Test filtering on large dataset
        category_transactions = temp_db.get_transactions_by_category("Category 0")
        assert len(category_transactions) == 20  # Every 5th transaction
    
    def test_data_consistency_workflow(self, temp_db, sample_transactions):
        """Test data consistency across operations."""
        # Insert initial data
        initial_ids = temp_db.insert_transactions_batch(sample_transactions)
        initial_count = temp_db.get_transaction_count()
        
        # Perform various operations
        temp_db.update_transaction_category(initial_ids[0], "New Category")
        temp_db.rename_category("Shopping", "Retail")
        
        # Verify count remains consistent
        final_count = temp_db.get_transaction_count()
        assert initial_count == final_count
        
        # Verify all transactions still retrievable
        all_transactions = temp_db.get_all_transactions()
        assert len(all_transactions) == len(sample_transactions)
        
        # Verify category consistency
        categories = temp_db.get_categories()
        stats = temp_db.get_category_stats()
        
        # All categories in stats should exist in categories list
        for category in stats.keys():
            assert category in categories