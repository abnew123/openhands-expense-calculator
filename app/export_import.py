"""Export and import utilities for transaction data."""

import json
import csv
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from io import StringIO, BytesIO
import logging

from app.models import Transaction
from app.db import DatabaseManager


class DataExporter:
    """Handle data export operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def export_to_csv(self, transactions: List[Transaction], include_metadata: bool = True) -> str:
        """Export transactions to CSV format."""
        if not transactions:
            return ""
        
        output = StringIO()
        
        # Add metadata as comments if requested
        if include_metadata:
            output.write(f"# Personal Expense Tracker Export\n")
            output.write(f"# Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            output.write(f"# Total Transactions: {len(transactions)}\n")
            output.write(f"# \n")
        
        # Write CSV header
        fieldnames = ['ID', 'Transaction Date', 'Post Date', 'Description', 'Category', 'Type', 'Amount', 'Memo']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write transaction data
        for transaction in transactions:
            writer.writerow({
                'ID': transaction.id,
                'Transaction Date': transaction.transaction_date.strftime('%m/%d/%Y'),
                'Post Date': transaction.post_date.strftime('%m/%d/%Y'),
                'Description': transaction.description,
                'Category': transaction.category,
                'Type': transaction.transaction_type,
                'Amount': float(transaction.amount),
                'Memo': transaction.memo or ''
            })
        
        csv_content = output.getvalue()
        output.close()
        
        self.logger.info(f"Exported {len(transactions)} transactions to CSV")
        return csv_content
    
    def export_to_json(self, transactions: List[Transaction] = None, pretty: bool = True) -> str:
        """Export transactions to JSON format."""
        export_data = self.db.export_transactions_to_dict(transactions)
        
        if pretty:
            json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
        else:
            json_content = json.dumps(export_data, ensure_ascii=False)
        
        self.logger.info(f"Exported {len(export_data['transactions'])} transactions to JSON")
        return json_content
    
    def export_category_stats_to_csv(self) -> str:
        """Export category statistics to CSV format."""
        stats = self.db.get_category_stats()
        
        if not stats:
            return ""
        
        output = StringIO()
        
        # Add metadata
        output.write(f"# Category Statistics Export\n")
        output.write(f"# Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output.write(f"# Total Categories: {len(stats)}\n")
        output.write(f"# \n")
        
        # Write CSV header
        fieldnames = ['Category', 'Transaction Count', 'Total Expenses', 'Total Income', 'Net Amount', 'First Transaction', 'Last Transaction']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write category data
        for category, stat in stats.items():
            writer.writerow({
                'Category': category,
                'Transaction Count': stat['transaction_count'],
                'Total Expenses': stat['total_expenses'],
                'Total Income': stat['total_income'],
                'Net Amount': stat['net_amount'],
                'First Transaction': stat['first_transaction'][:10] if stat['first_transaction'] else '',
                'Last Transaction': stat['last_transaction'][:10] if stat['last_transaction'] else ''
            })
        
        csv_content = output.getvalue()
        output.close()
        
        self.logger.info(f"Exported statistics for {len(stats)} categories to CSV")
        return csv_content


class DataImporter:
    """Handle data import operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def import_from_json(self, json_content: str) -> Dict[str, int]:
        """Import transactions from JSON format."""
        try:
            import_data = json.loads(json_content)
            result = self.db.import_transactions_from_dict(import_data)
            
            self.logger.info(f"JSON import completed: {result}")
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format: {e}")
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            self.logger.error(f"JSON import failed: {e}")
            raise
    
    def validate_json_import(self, json_content: str) -> Dict[str, Any]:
        """Validate JSON import data and return summary."""
        try:
            import_data = json.loads(json_content)
            
            # Check required fields
            if 'transactions' not in import_data:
                raise ValueError("Missing 'transactions' field in import data")
            
            transactions_data = import_data['transactions']
            
            # Validate transaction structure
            valid_transactions = 0
            invalid_transactions = 0
            categories = set()
            
            for transaction_dict in transactions_data:
                try:
                    # Try to create transaction to validate structure
                    Transaction.from_dict(transaction_dict)
                    valid_transactions += 1
                    
                    if 'category' in transaction_dict:
                        categories.add(transaction_dict['category'])
                        
                except Exception:
                    invalid_transactions += 1
            
            validation_result = {
                'valid': True,
                'total_transactions': len(transactions_data),
                'valid_transactions': valid_transactions,
                'invalid_transactions': invalid_transactions,
                'categories_found': list(categories),
                'metadata': import_data.get('metadata', {}),
                'has_category_stats': 'category_stats' in import_data
            }
            
            if invalid_transactions > 0:
                validation_result['valid'] = False
                validation_result['warning'] = f"{invalid_transactions} transactions have invalid format"
            
            return validation_result
            
        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'error': f"Invalid JSON format: {e}",
                'total_transactions': 0,
                'valid_transactions': 0,
                'invalid_transactions': 0
            }
        except Exception as e:
            return {
                'valid': False,
                'error': f"Validation failed: {e}",
                'total_transactions': 0,
                'valid_transactions': 0,
                'invalid_transactions': 0
            }


def create_download_link(content: str, filename: str, content_type: str = "text/plain") -> str:
    """Create a download link for content."""
    import base64
    
    # Encode content for download
    b64_content = base64.b64encode(content.encode()).decode()
    
    # Create download link
    download_link = f'<a href="data:{content_type};base64,{b64_content}" download="{filename}">📥 Download {filename}</a>'
    
    return download_link