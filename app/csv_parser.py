import pandas as pd
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from io import StringIO

from app.models import Transaction


class CSVParser:
    """Parses CSV files in various bank formats and converts to Transaction objects."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_csv_format(self, csv_content: str, format_type: str = "chase") -> bool:
        """Validate if CSV content matches the expected format."""
        try:
            df = pd.read_csv(StringIO(csv_content))
            
            if format_type.lower() == "chase":
                required_columns = ['Transaction Date', 'Post Date', 'Description', 'Category', 'Type', 'Amount', 'Memo']
                return all(col in df.columns for col in required_columns)
            
            return False
        except Exception as e:
            self.logger.error(f"CSV validation failed: {e}")
            return False
    
    def get_csv_preview(self, csv_content: str, max_rows: int = 5) -> pd.DataFrame:
        """Get a preview of the CSV content."""
        try:
            df = pd.read_csv(StringIO(csv_content))
            return df.head(max_rows)
        except Exception as e:
            self.logger.error(f"CSV preview failed: {e}")
            return pd.DataFrame()
    
    def parse_chase_csv(self, csv_content: str) -> List[Transaction]:
        """Parse Chase credit card CSV format."""
        try:
            # Read CSV content
            df = pd.read_csv(StringIO(csv_content))
            
            # Validate required columns
            required_columns = ['Transaction Date', 'Post Date', 'Description', 'Category', 'Type', 'Amount', 'Memo']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            transactions = []
            
            for index, row in df.iterrows():
                try:
                    # Parse dates - handle MM/DD/YYYY format
                    transaction_date = self._parse_date(row['Transaction Date'])
                    post_date = self._parse_date(row['Post Date'])
                    
                    # Parse amount
                    amount = Decimal(str(row['Amount']))
                    
                    # Handle category - use 'Uncategorized' if empty
                    category = str(row['Category']).strip() if pd.notna(row['Category']) else "Uncategorized"
                    if not category:
                        category = "Uncategorized"
                    
                    # Handle memo
                    memo = str(row['Memo']).strip() if pd.notna(row['Memo']) else None
                    if memo == "":
                        memo = None
                    
                    transaction = Transaction(
                        transaction_date=transaction_date,
                        post_date=post_date,
                        description=str(row['Description']).strip(),
                        category=category,
                        transaction_type=str(row['Type']).strip(),
                        amount=amount,
                        memo=memo
                    )
                    
                    transactions.append(transaction)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse row {index + 1}: {e}")
                    continue
            
            self.logger.info(f"Successfully parsed {len(transactions)} transactions from CSV")
            return transactions
            
        except Exception as e:
            self.logger.error(f"Failed to parse CSV: {e}")
            raise
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in various formats."""
        if pd.isna(date_str):
            raise ValueError("Date cannot be empty")
        
        date_str = str(date_str).strip()
        
        # Try common date formats
        date_formats = [
            '%m/%d/%Y',    # MM/DD/YYYY (Chase format)
            '%Y-%m-%d',    # YYYY-MM-DD (ISO format)
            '%m-%d-%Y',    # MM-DD-YYYY
            '%d/%m/%Y',    # DD/MM/YYYY
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse date: {date_str}")
    
    def validate_csv_format(self, csv_content: str, format_type: str = "chase") -> bool:
        """Validate that CSV content matches expected format."""
        try:
            if format_type.lower() == "chase":
                df = pd.read_csv(StringIO(csv_content))
                required_columns = ['Transaction Date', 'Post Date', 'Description', 'Category', 'Type', 'Amount', 'Memo']
                return all(col in df.columns for col in required_columns)
            else:
                raise ValueError(f"Unsupported format type: {format_type}")
        except Exception as e:
            self.logger.error(f"CSV validation failed: {e}")
            return False
    
    def get_csv_preview(self, csv_content: str, max_rows: int = 5) -> pd.DataFrame:
        """Get a preview of the CSV data for user verification."""
        try:
            df = pd.read_csv(StringIO(csv_content))
            return df.head(max_rows)
        except Exception as e:
            self.logger.error(f"Failed to generate CSV preview: {e}")
            raise
    
    def detect_csv_format(self, csv_content: str) -> Optional[str]:
        """Attempt to detect the CSV format based on column headers."""
        try:
            df = pd.read_csv(StringIO(csv_content))
            columns = set(df.columns)
            
            # Check for Chase format
            chase_columns = {'Transaction Date', 'Post Date', 'Description', 'Category', 'Type', 'Amount', 'Memo'}
            if chase_columns.issubset(columns):
                return "chase"
            
            # Could add other bank formats here in the future
            
            return None
        except Exception as e:
            self.logger.error(f"Failed to detect CSV format: {e}")
            return None