"""Tests for CSV parser functionality."""

import pytest
from datetime import datetime

from app.csv_parser import CSVParser


class TestCSVParser:
    """Test CSV parser functionality."""
    
    def test_validate_csv_format_valid(self, csv_parser, sample_csv_content):
        """Test CSV format validation with valid content."""
        result = csv_parser.validate_csv_format(sample_csv_content, "chase")
        assert result['valid'] is True
    
    def test_validate_csv_format_invalid(self, csv_parser, invalid_csv_content):
        """Test CSV format validation with invalid content."""
        result = csv_parser.validate_csv_format(invalid_csv_content, "chase")
        assert result['valid'] is False
    
    def test_validate_csv_format_empty(self, csv_parser):
        """Test CSV format validation with empty content."""
        result = csv_parser.validate_csv_format("", "chase")
        assert result['valid'] is False
    
    def test_validate_csv_format_unsupported_format(self, csv_parser, sample_csv_content):
        """Test CSV format validation with unsupported format."""
        result = csv_parser.validate_csv_format(sample_csv_content, "unsupported")
        assert result['valid'] is False
    
    def test_get_csv_preview(self, csv_parser, sample_csv_content):
        """Test CSV preview functionality."""
        preview_df = csv_parser.get_csv_preview(sample_csv_content)
        
        assert len(preview_df) == 5  # 5 sample transactions
        assert 'Transaction Date' in preview_df.columns
        assert 'Description' in preview_df.columns
        assert 'Amount' in preview_df.columns
        
        # Check first row
        first_row = preview_df.iloc[0]
        assert first_row['Description'] == 'STARBUCKS STORE #12345'
        assert first_row['Amount'] == -4.75
    
    def test_get_csv_preview_empty(self, csv_parser):
        """Test CSV preview with empty content."""
        preview_df = csv_parser.get_csv_preview("")
        assert len(preview_df) == 0
    
    def test_parse_chase_csv(self, csv_parser, sample_csv_content):
        """Test parsing Chase CSV format."""
        transactions = csv_parser.parse_chase_csv(sample_csv_content)
        
        assert len(transactions) == 5
        
        # Test first transaction
        first_transaction = transactions[0]
        assert first_transaction.transaction_date == datetime(2024, 1, 15)
        assert first_transaction.post_date == datetime(2024, 1, 16)
        assert first_transaction.description == "STARBUCKS STORE #12345"
        assert first_transaction.category == "Food & Drink"
        assert first_transaction.transaction_type == "Sale"
        assert float(first_transaction.amount) == -4.75
        assert first_transaction.memo is None
        
        # Test payment transaction
        payment_transaction = transactions[2]
        assert payment_transaction.description == "PAYMENT THANK YOU - WEB"
        assert payment_transaction.transaction_type == "Payment"
        assert float(payment_transaction.amount) == 150.00
        assert payment_transaction.is_payment() is True
        
        # Test expense transaction
        expense_transaction = transactions[1]
        assert expense_transaction.description == "AMAZON.COM AMZN.COM/BILL"
        assert expense_transaction.is_expense() is True
    
    def test_parse_chase_csv_empty(self, csv_parser):
        """Test parsing empty CSV."""
        transactions = csv_parser.parse_chase_csv("")
        assert len(transactions) == 0
    
    def test_parse_chase_csv_invalid_format(self, csv_parser, invalid_csv_content):
        """Test parsing invalid CSV format."""
        transactions = csv_parser.parse_chase_csv(invalid_csv_content)
        assert len(transactions) == 0
    
    def test_parse_chase_csv_malformed_data(self, csv_parser):
        """Test parsing CSV with malformed data."""
        malformed_csv = """Transaction Date,Post Date,Description,Category,Type,Amount,Memo
invalid_date,01/16/2024,STARBUCKS,Food,Sale,-4.75,
01/16/2024,invalid_date,AMAZON,Shopping,Sale,invalid_amount,"""
        
        transactions = csv_parser.parse_chase_csv(malformed_csv)
        # Should skip malformed rows
        assert len(transactions) == 0
    
    def test_parse_chase_csv_missing_columns(self, csv_parser):
        """Test parsing CSV with missing required columns."""
        incomplete_csv = """Date,Description,Amount
01/15/2024,STARBUCKS,-4.75"""
        
        transactions = csv_parser.parse_chase_csv(incomplete_csv)
        assert len(transactions) == 0
    
    def test_parse_chase_csv_extra_whitespace(self, csv_parser):
        """Test parsing CSV with extra whitespace."""
        whitespace_csv = """Transaction Date,Post Date,Description,Category,Type,Amount,Memo
 01/15/2024 , 01/16/2024 , STARBUCKS STORE #12345 , Food & Drink , Sale , -4.75 , """
        
        transactions = csv_parser.parse_chase_csv(whitespace_csv)
        assert len(transactions) == 1
        
        transaction = transactions[0]
        assert transaction.description.strip() == "STARBUCKS STORE #12345"
        assert transaction.category.strip() == "Food & Drink"
    
    def test_date_parsing_formats(self, csv_parser):
        """Test different date formats are handled correctly."""
        date_format_csv = """Transaction Date,Post Date,Description,Category,Type,Amount,Memo
01/15/2024,01/16/2024,TEST1,Food,Sale,-10.00,
1/15/2024,1/16/2024,TEST2,Food,Sale,-10.00,"""
        
        transactions = csv_parser.parse_chase_csv(date_format_csv)
        assert len(transactions) == 2
        
        # Both should parse to the same date
        assert transactions[0].transaction_date == datetime(2024, 1, 15)
        assert transactions[1].transaction_date == datetime(2024, 1, 15)