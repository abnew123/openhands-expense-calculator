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
        
        # Define supported CSV formats
        self.formats = {
            'chase': {
                'name': 'Chase Credit Card',
                'required_columns': ['Transaction Date', 'Post Date', 'Description', 'Category', 'Type', 'Amount', 'Memo'],
                'column_mapping': {
                    'transaction_date': 'Transaction Date',
                    'post_date': 'Post Date',
                    'description': 'Description',
                    'category': 'Category',
                    'transaction_type': 'Type',
                    'amount': 'Amount',
                    'memo': 'Memo'
                },
                'date_format': '%m/%d/%Y'
            },
            'bank_of_america': {
                'name': 'Bank of America',
                'required_columns': ['Date', 'Description', 'Amount', 'Running Bal.'],
                'column_mapping': {
                    'transaction_date': 'Date',
                    'post_date': 'Date',  # Use same date for both
                    'description': 'Description',
                    'category': None,  # Will be set to 'Uncategorized'
                    'transaction_type': None,  # Will be determined from amount
                    'amount': 'Amount',
                    'memo': None
                },
                'date_format': '%m/%d/%Y'
            },
            'american_express': {
                'name': 'American Express',
                'required_columns': ['Date', 'Description', 'Amount'],
                'column_mapping': {
                    'transaction_date': 'Date',
                    'post_date': 'Date',  # Use same date for both
                    'description': 'Description',
                    'category': None,  # Will be set to 'Uncategorized'
                    'transaction_type': None,  # Will be determined from amount
                    'amount': 'Amount',
                    'memo': None
                },
                'date_format': '%m/%d/%Y'
            },
            'wells_fargo': {
                'name': 'Wells Fargo',
                'required_columns': ['Date', 'Amount', 'Description'],
                'column_mapping': {
                    'transaction_date': 'Date',
                    'post_date': 'Date',  # Use same date for both
                    'description': 'Description',
                    'category': None,  # Will be set to 'Uncategorized'
                    'transaction_type': None,  # Will be determined from amount
                    'amount': 'Amount',
                    'memo': None
                },
                'date_format': '%m/%d/%Y'
            },
            'wells_fargo_headerless': {
                'name': 'Wells Fargo (No Headers)',
                'required_columns': [],  # No headers to check
                'column_mapping': {
                    'transaction_date': 0,  # First column (index)
                    'post_date': 0,  # Use same date for both
                    'description': 2,  # Third column (index)
                    'category': None,  # Will be set to 'Uncategorized'
                    'transaction_type': None,  # Will be determined from amount
                    'amount': 1,  # Second column (index)
                    'memo': None
                },
                'date_format': '%m/%d/%Y',
                'headerless': True
            },
            'capital_one': {
                'name': 'Capital One',
                'required_columns': ['Transaction Date', 'Posted Date', 'Card No.', 'Description', 'Category', 'Debit', 'Credit'],
                'column_mapping': {
                    'transaction_date': 'Transaction Date',
                    'post_date': 'Posted Date',
                    'description': 'Description',
                    'category': 'Category',
                    'transaction_type': None,  # Will be determined from debit/credit
                    'amount': None,  # Special handling for debit/credit columns
                    'memo': None
                },
                'date_format': '%Y-%m-%d'
            }
        }
    
    def validate_csv_format(self, csv_content: str, format_type: str = "auto") -> dict:
        """Validate if CSV content matches the expected format and return detailed results."""
        result = {
            'valid': False,
            'detected_format': None,
            'error_message': '',
            'missing_columns': [],
            'extra_columns': [],
            'actual_columns': [],
            'expected_columns': []
        }
        
        try:
            if not csv_content or not csv_content.strip():
                result['error_message'] = "CSV content is empty"
                return result
            
            df = pd.read_csv(StringIO(csv_content))
            result['actual_columns'] = list(df.columns)
            
            if format_type == "auto":
                # Try to detect format automatically
                detected_format = self.detect_csv_format(csv_content)
                result['detected_format'] = detected_format
                
                if detected_format is None:
                    result['error_message'] = f"Could not detect CSV format. Found columns: {result['actual_columns']}"
                    return result
                
                format_spec = self.formats[detected_format]
                result['expected_columns'] = format_spec['required_columns']
                
                # Check if all required columns are present
                missing = [col for col in format_spec['required_columns'] if col not in df.columns]
                extra = [col for col in df.columns if col not in format_spec['required_columns']]
                
                result['missing_columns'] = missing
                result['extra_columns'] = extra
                
                if not missing:
                    result['valid'] = True
                else:
                    result['error_message'] = f"Missing required columns for {format_spec['name']}: {missing}"
                
                return result
            
            if format_type.lower() in self.formats:
                format_spec = self.formats[format_type.lower()]
                result['expected_columns'] = format_spec['required_columns']
                result['detected_format'] = format_type.lower()
                
                # Handle headerless formats
                if format_spec.get('headerless', False):
                    # For headerless formats, validate by checking column count and data patterns
                    expected_columns = len([k for k, v in format_spec['column_mapping'].items() if v is not None and isinstance(v, int)])
                    actual_columns = len(df.columns)
                    
                    if actual_columns >= expected_columns:
                        result['valid'] = True
                        result['expected_columns'] = [f"Column {i}" for i in range(expected_columns)]
                    else:
                        result['error_message'] = f"Expected at least {expected_columns} columns for {format_spec['name']}, found {actual_columns}"
                    
                    return result
                
                missing = [col for col in format_spec['required_columns'] if col not in df.columns]
                extra = [col for col in df.columns if col not in format_spec['required_columns']]
                
                result['missing_columns'] = missing
                result['extra_columns'] = extra
                
                if not missing:
                    result['valid'] = True
                else:
                    result['error_message'] = f"Missing required columns for {format_spec['name']}: {missing}"
                
                return result
            
            result['error_message'] = f"Unsupported format type: {format_type}"
            return result
            
        except Exception as e:
            result['error_message'] = f"CSV validation failed: {str(e)}"
            self.logger.error(f"CSV validation failed: {e}")
            return result
    
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
            # Handle empty content
            if not csv_content or not csv_content.strip():
                return []
            
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
            return []
    
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
    

    
    def get_csv_preview(self, csv_content: str, max_rows: int = 5) -> pd.DataFrame:
        """Get a preview of the CSV data for user verification."""
        try:
            # Handle empty content
            if not csv_content or not csv_content.strip():
                return pd.DataFrame()
            
            df = pd.read_csv(StringIO(csv_content))
            return df.head(max_rows)
        except Exception as e:
            self.logger.error(f"Failed to generate CSV preview: {e}")
            return pd.DataFrame()
    
    def detect_csv_format(self, csv_content: str) -> Optional[str]:
        """Attempt to detect the CSV format based on column headers or data patterns."""
        try:
            if not csv_content or not csv_content.strip():
                return None
            
            # First try with headers
            df = pd.read_csv(StringIO(csv_content))
            columns = set(df.columns)
            
            # Check each format in order of specificity (most specific first)
            for format_name, format_spec in self.formats.items():
                required_columns = set(format_spec['required_columns'])
                if required_columns.issubset(columns):
                    self.logger.info(f"Detected CSV format: {format_spec['name']}")
                    return format_name
            
            # If no format detected with headers, try detecting headerless formats
            headerless_format = self._detect_headerless_format(csv_content)
            if headerless_format:
                return headerless_format
            
            self.logger.warning(f"Unknown CSV format with columns: {list(columns)}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to detect CSV format: {e}")
            return None
    
    def _detect_headerless_format(self, csv_content: str) -> Optional[str]:
        """Detect CSV format for files without headers by analyzing data patterns."""
        try:
            lines = csv_content.strip().split('\n')
            if len(lines) < 2:
                return None
            
            # Analyze first few lines to detect patterns
            first_line = lines[0].split(',')
            
            # Wells Fargo pattern: Date, Amount, Description (3 columns)
            if len(first_line) == 3:
                # Check if first column looks like a date
                date_col = first_line[0].strip()
                amount_col = first_line[1].strip()
                
                # Simple date pattern check (MM/DD/YYYY or similar)
                if ('/' in date_col and len(date_col.split('/')) == 3) or ('-' in date_col and len(date_col.split('-')) == 3):
                    # Check if second column looks like an amount
                    try:
                        float(amount_col)
                        self.logger.info("Detected headerless Wells Fargo format")
                        return 'wells_fargo_headerless'
                    except ValueError:
                        pass
            
            return None
        except Exception as e:
            self.logger.error(f"Failed to detect headerless format: {e}")
            return None
    
    def _parse_headerless_csv(self, csv_content: str, format_spec: dict) -> List[Transaction]:
        """Parse CSV content without headers using column indices."""
        try:
            # Read CSV without headers
            df = pd.read_csv(StringIO(csv_content), header=None)
            
            transactions = []
            column_mapping = format_spec['column_mapping']
            date_format = format_spec['date_format']
            
            for index, row in df.iterrows():
                try:
                    # Parse dates using column indices
                    transaction_date = self._parse_date_with_format(
                        row[column_mapping['transaction_date']], date_format
                    )
                    
                    if column_mapping['post_date'] is not None:
                        post_date = self._parse_date_with_format(
                            row[column_mapping['post_date']], date_format
                        )
                    else:
                        post_date = transaction_date  # Use transaction date as post date
                    
                    # Parse amount using column index
                    amount_value = row[column_mapping['amount']]
                    if pd.isna(amount_value):
                        continue
                    
                    try:
                        # Handle different amount formats
                        amount_str = str(amount_value).strip()
                        # Remove currency symbols and commas
                        amount_str = amount_str.replace('$', '').replace(',', '')
                        amount = Decimal(amount_str)
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid amount in row {index + 1}: {amount_value}")
                        continue
                    
                    # Get description using column index
                    description = str(row[column_mapping['description']]).strip()
                    if not description:
                        description = "Unknown Transaction"
                    
                    # Set default category
                    category = "Uncategorized"
                    
                    # Determine transaction type from amount
                    transaction_type = "Payment" if amount > 0 else "Sale"
                    
                    # No memo for headerless format
                    memo = None
                    
                    transaction = Transaction(
                        transaction_date=transaction_date,
                        post_date=post_date,
                        description=description,
                        category=category,
                        transaction_type=transaction_type,
                        amount=amount,
                        memo=memo
                    )
                    
                    transactions.append(transaction)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse headerless row {index + 1}: {e}")
                    continue
            
            self.logger.info(f"Successfully parsed {len(transactions)} transactions from headerless {format_spec['name']} CSV")
            return transactions
            
        except Exception as e:
            self.logger.error(f"Failed to parse headerless CSV: {e}")
            return []
    
    def get_supported_formats(self) -> dict:
        """Get information about all supported CSV formats."""
        return {
            format_name: {
                'name': format_spec['name'],
                'required_columns': format_spec['required_columns']
            }
            for format_name, format_spec in self.formats.items()
        }
    
    def parse_csv_auto(self, csv_content: str) -> List[Transaction]:
        """Parse CSV content with automatic format detection."""
        detected_format = self.detect_csv_format(csv_content)
        
        if not detected_format:
            self.logger.error("Could not detect CSV format")
            return []
        
        return self.parse_csv_generic(csv_content, detected_format)
    
    def parse_csv_generic(self, csv_content: str, format_type: str) -> List[Transaction]:
        """Parse CSV content using the specified format."""
        try:
            # Handle empty content
            if not csv_content or not csv_content.strip():
                return []
            
            if format_type not in self.formats:
                raise ValueError(f"Unsupported format: {format_type}")
            
            format_spec = self.formats[format_type]
            
            # Handle headerless formats
            if format_spec.get('headerless', False):
                return self._parse_headerless_csv(csv_content, format_spec)
            
            # Read CSV content with headers
            df = pd.read_csv(StringIO(csv_content))
            
            # Validate required columns
            required_columns = format_spec['required_columns']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns for {format_spec['name']}: {missing_columns}")
            
            transactions = []
            column_mapping = format_spec['column_mapping']
            date_format = format_spec['date_format']
            
            for index, row in df.iterrows():
                try:
                    # Parse dates
                    transaction_date = self._parse_date_with_format(
                        row[column_mapping['transaction_date']], date_format
                    )
                    
                    if column_mapping['post_date']:
                        post_date = self._parse_date_with_format(
                            row[column_mapping['post_date']], date_format
                        )
                    else:
                        post_date = transaction_date  # Use transaction date as post date
                    
                    # Parse amount - handle special cases like Capital One debit/credit columns
                    if format_type == 'capital_one':
                        # Capital One has separate Debit and Credit columns
                        debit_value = row.get('Debit', 0) or 0
                        credit_value = row.get('Credit', 0) or 0
                        
                        try:
                            debit_amount = Decimal(str(debit_value).replace('$', '').replace(',', '')) if debit_value else Decimal('0')
                            credit_amount = Decimal(str(credit_value).replace('$', '').replace(',', '')) if credit_value else Decimal('0')
                            
                            # Debit is negative (expense), Credit is positive (payment/refund)
                            amount = credit_amount - debit_amount
                        except (ValueError, TypeError):
                            self.logger.warning(f"Invalid debit/credit amounts in row {index + 1}: debit={debit_value}, credit={credit_value}")
                            continue
                    else:
                        # Standard amount column handling
                        amount_value = row[column_mapping['amount']]
                        if pd.isna(amount_value):
                            continue
                        
                        try:
                            # Handle different amount formats
                            amount_str = str(amount_value).strip()
                            # Remove currency symbols and commas
                            amount_str = amount_str.replace('$', '').replace(',', '')
                            amount = Decimal(amount_str)
                        except (ValueError, TypeError):
                            self.logger.warning(f"Invalid amount in row {index + 1}: {amount_value}")
                            continue
                    
                    # Get description
                    description = str(row[column_mapping['description']]).strip()
                    if not description:
                        description = "Unknown Transaction"
                    
                    # Get category
                    if column_mapping['category'] and column_mapping['category'] in row:
                        category = str(row[column_mapping['category']]).strip()
                        if not category or pd.isna(row[column_mapping['category']]):
                            category = "Uncategorized"
                    else:
                        category = "Uncategorized"
                    
                    # Get transaction type
                    if column_mapping['transaction_type'] and column_mapping['transaction_type'] in row:
                        transaction_type = str(row[column_mapping['transaction_type']]).strip()
                    else:
                        # Determine type from amount
                        transaction_type = "Payment" if amount > 0 else "Sale"
                    
                    # Get memo
                    memo = None
                    if column_mapping['memo'] and column_mapping['memo'] in row:
                        memo_value = row[column_mapping['memo']]
                        if pd.notna(memo_value):
                            memo = str(memo_value).strip()
                            if memo == "":
                                memo = None
                    
                    transaction = Transaction(
                        transaction_date=transaction_date,
                        post_date=post_date,
                        description=description,
                        category=category,
                        transaction_type=transaction_type,
                        amount=amount,
                        memo=memo
                    )
                    
                    transactions.append(transaction)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse row {index + 1} in {format_spec['name']} format: {e}")
                    continue
            
            self.logger.info(f"Successfully parsed {len(transactions)} transactions from {format_spec['name']} CSV")
            return transactions
            
        except Exception as e:
            self.logger.error(f"Failed to parse {format_type} CSV: {e}")
            return []
    
    def _parse_date_with_format(self, date_str: str, date_format: str) -> datetime:
        """Parse date string with specific format, with fallback to generic parsing."""
        if pd.isna(date_str):
            raise ValueError("Date cannot be empty")
        
        date_str = str(date_str).strip()
        
        # Try the specified format first
        try:
            return datetime.strptime(date_str, date_format)
        except ValueError:
            # Fall back to generic date parsing
            return self._parse_date(date_str)