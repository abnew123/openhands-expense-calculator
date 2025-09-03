import sqlite3
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from app.models import Transaction


class DatabaseManager:
    """Manages SQLite database operations for expense tracking."""
    
    def __init__(self, db_path: str = None):
        """Initialize database manager with specified database path."""
        if db_path is None:
            # Use data directory for persistence in containers
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "expenses.db")
        
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transaction_date TEXT NOT NULL,
                        post_date TEXT NOT NULL,
                        description TEXT NOT NULL,
                        category TEXT NOT NULL DEFAULT 'Uncategorized',
                        transaction_type TEXT NOT NULL,
                        amount REAL NOT NULL,
                        memo TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for common queries
                conn.execute("CREATE INDEX IF NOT EXISTS idx_transaction_date ON transactions(transaction_date)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON transactions(category)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_amount ON transactions(amount)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON transactions(transaction_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_description ON transactions(description)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_date_category ON transactions(transaction_date, category)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_date_amount ON transactions(transaction_date, amount)")
                
                conn.commit()
                self.logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    def insert_transaction(self, transaction: Transaction) -> int:
        """Insert a single transaction and return its ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO transactions 
                    (transaction_date, post_date, description, category, transaction_type, amount, memo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction.transaction_date.isoformat(),
                    transaction.post_date.isoformat(),
                    transaction.description,
                    transaction.category,
                    transaction.transaction_type,
                    float(transaction.amount),
                    transaction.memo
                ))
                transaction_id = cursor.lastrowid
                conn.commit()
                self.logger.info(f"Inserted transaction with ID {transaction_id}")
                return transaction_id
        except sqlite3.Error as e:
            self.logger.error(f"Failed to insert transaction: {e}")
            raise
    
    def insert_transactions_batch(self, transactions: List[Transaction]) -> List[int]:
        """Insert multiple transactions in a batch operation."""
        if not transactions:
            return []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                transaction_data = [
                    (
                        t.transaction_date.isoformat(),
                        t.post_date.isoformat(),
                        t.description,
                        t.category,
                        t.transaction_type,
                        float(t.amount),
                        t.memo
                    ) for t in transactions
                ]
                
                cursor.executemany("""
                    INSERT INTO transactions 
                    (transaction_date, post_date, description, category, transaction_type, amount, memo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, transaction_data)
                
                # Get the IDs of inserted transactions
                if cursor.lastrowid is not None:
                    first_id = cursor.lastrowid - len(transactions) + 1
                    transaction_ids = list(range(first_id, cursor.lastrowid + 1))
                else:
                    # Fallback: query for the last inserted IDs
                    cursor.execute("SELECT id FROM transactions ORDER BY id DESC LIMIT ?", (len(transactions),))
                    transaction_ids = [row[0] for row in cursor.fetchall()]
                    transaction_ids.reverse()  # Restore insertion order
                
                conn.commit()
                self.logger.info(f"Inserted {len(transactions)} transactions")
                return transaction_ids
        except sqlite3.Error as e:
            self.logger.error(f"Failed to insert transactions batch: {e}")
            raise
    
    def get_all_transactions(self) -> List[Transaction]:
        """Retrieve all transactions from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM transactions 
                    ORDER BY transaction_date DESC, id DESC
                """)
                rows = cursor.fetchall()
                
                transactions = []
                for row in rows:
                    transaction = Transaction.from_dict(dict(row))
                    transactions.append(transaction)
                
                self.logger.info(f"Retrieved {len(transactions)} transactions")
                return transactions
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve transactions: {e}")
            raise
    
    def get_transactions_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Transaction]:
        """Retrieve transactions within a specific date range."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM transactions 
                    WHERE transaction_date >= ? AND transaction_date <= ?
                    ORDER BY transaction_date DESC, id DESC
                """, (start_date.isoformat(), end_date.isoformat()))
                rows = cursor.fetchall()
                
                transactions = []
                for row in rows:
                    transaction = Transaction.from_dict(dict(row))
                    transactions.append(transaction)
                
                self.logger.info(f"Retrieved {len(transactions)} transactions for date range")
                return transactions
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve transactions by date range: {e}")
            raise
    
    def get_transactions_by_category(self, category: str) -> List[Transaction]:
        """Retrieve transactions for a specific category."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM transactions 
                    WHERE category = ?
                    ORDER BY transaction_date DESC, id DESC
                """, (category,))
                rows = cursor.fetchall()
                
                transactions = []
                for row in rows:
                    transaction = Transaction.from_dict(dict(row))
                    transactions.append(transaction)
                
                return transactions
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve transactions by category: {e}")
            raise
    
    def update_transaction_category(self, transaction_id: int, new_category: str) -> bool:
        """Update the category of a specific transaction."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE transactions 
                    SET category = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_category, transaction_id))
                
                if cursor.rowcount == 0:
                    self.logger.warning(f"No transaction found with ID {transaction_id}")
                    return False
                
                conn.commit()
                self.logger.info(f"Updated category for transaction {transaction_id} to '{new_category}'")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update transaction category: {e}")
            raise
    
    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a specific transaction."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
                
                if cursor.rowcount == 0:
                    self.logger.warning(f"No transaction found with ID {transaction_id}")
                    return False
                
                conn.commit()
                self.logger.info(f"Deleted transaction {transaction_id}")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Failed to delete transaction: {e}")
            raise
    
    def get_categories(self) -> List[str]:
        """Get all unique categories from transactions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT category FROM transactions 
                    WHERE category IS NOT NULL AND category != ''
                    ORDER BY category
                """)
                categories = [row[0] for row in cursor.fetchall()]
                return categories
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve categories: {e}")
            raise
    
    def get_transaction_count(self) -> int:
        """Get total number of transactions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM transactions")
                count = cursor.fetchone()[0]
                return count
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get transaction count: {e}")
            raise
    
    def transaction_exists(self, transaction: Transaction) -> bool:
        """Check if a transaction already exists (duplicate detection)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM transactions 
                    WHERE transaction_date = ? AND post_date = ? 
                    AND description = ? AND amount = ?
                """, (
                    transaction.transaction_date.isoformat(),
                    transaction.post_date.isoformat(),
                    transaction.description,
                    float(transaction.amount)
                ))
                count = cursor.fetchone()[0]
                return count > 0
        except sqlite3.Error as e:
            self.logger.error(f"Failed to check transaction existence: {e}")
            raise
    
    def rename_category(self, old_category: str, new_category: str) -> int:
        """Rename a category across all transactions. Returns number of transactions updated."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE transactions 
                    SET category = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE category = ?
                """, (new_category, old_category))
                
                updated_count = cursor.rowcount
                conn.commit()
                self.logger.info(f"Renamed category '{old_category}' to '{new_category}' for {updated_count} transactions")
                return updated_count
        except sqlite3.Error as e:
            self.logger.error(f"Failed to rename category: {e}")
            raise
    
    def merge_categories(self, categories_to_merge: List[str], target_category: str) -> int:
        """Merge multiple categories into a target category. Returns number of transactions updated."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                placeholders = ','.join(['?' for _ in categories_to_merge])
                cursor = conn.execute(f"""
                    UPDATE transactions 
                    SET category = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE category IN ({placeholders})
                """, [target_category] + categories_to_merge)
                
                updated_count = cursor.rowcount
                conn.commit()
                self.logger.info(f"Merged {len(categories_to_merge)} categories into '{target_category}' for {updated_count} transactions")
                return updated_count
        except sqlite3.Error as e:
            self.logger.error(f"Failed to merge categories: {e}")
            raise
    
    def delete_category(self, category: str, replacement_category: str = "Uncategorized") -> int:
        """Delete a category by replacing it with a replacement category. Returns number of transactions updated."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE transactions 
                    SET category = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE category = ?
                """, (replacement_category, category))
                
                updated_count = cursor.rowcount
                conn.commit()
                self.logger.info(f"Deleted category '{category}', replaced with '{replacement_category}' for {updated_count} transactions")
                return updated_count
        except sqlite3.Error as e:
            self.logger.error(f"Failed to delete category: {e}")
            raise
    
    def get_category_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each category including transaction count and total amounts."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        category,
                        COUNT(*) as transaction_count,
                        SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as total_expenses,
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
                        SUM(amount) as net_amount,
                        MIN(transaction_date) as first_transaction,
                        MAX(transaction_date) as last_transaction
                    FROM transactions 
                    GROUP BY category
                    ORDER BY transaction_count DESC
                """)
                
                stats = {}
                for row in cursor.fetchall():
                    stats[row[0]] = {
                        'transaction_count': row[1],
                        'total_expenses': abs(row[2]) if row[2] else 0,
                        'total_income': row[3] if row[3] else 0,
                        'net_amount': row[4],
                        'first_transaction': row[5],
                        'last_transaction': row[6]
                    }
                
                return stats
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get category stats: {e}")
            raise
    
    def export_transactions_to_dict(self, transactions: List[Transaction] = None) -> Dict[str, Any]:
        """Export transactions to dictionary format for JSON export."""
        if transactions is None:
            transactions = self.get_all_transactions()
        
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'version': '1.0',
                'total_transactions': len(transactions),
                'application': 'Personal Expense Tracker'
            },
            'transactions': [t.to_dict() for t in transactions],
            'categories': self.get_categories(),
            'category_stats': self.get_category_stats()
        }
        
        return export_data
    
    def import_transactions_from_dict(self, import_data: Dict[str, Any]) -> Dict[str, int]:
        """Import transactions from dictionary format (JSON import)."""
        try:
            # Validate import data structure
            if 'transactions' not in import_data:
                raise ValueError("Invalid import data: missing 'transactions' key")
            
            transactions_data = import_data['transactions']
            imported_count = 0
            duplicate_count = 0
            error_count = 0
            
            for transaction_dict in transactions_data:
                try:
                    # Create transaction from dict
                    transaction = Transaction.from_dict(transaction_dict)
                    
                    # Check for duplicates
                    if not self.transaction_exists(transaction):
                        self.insert_transaction(transaction)
                        imported_count += 1
                    else:
                        duplicate_count += 1
                        
                except Exception as e:
                    self.logger.warning(f"Failed to import transaction: {e}")
                    error_count += 1
                    continue
            
            self.logger.info(f"Import completed: {imported_count} imported, {duplicate_count} duplicates, {error_count} errors")
            
            return {
                'imported': imported_count,
                'duplicates': duplicate_count,
                'errors': error_count,
                'total_processed': len(transactions_data)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to import transactions: {e}")
            raise
    
    def get_transactions_paginated(self, page: int = 1, page_size: int = 50, 
                                 order_by: str = "transaction_date", 
                                 order_desc: bool = True) -> List[Transaction]:
        """Get transactions with pagination for better performance."""
        try:
            offset = (page - 1) * page_size
            order_direction = "DESC" if order_desc else "ASC"
            
            # Validate order_by column to prevent SQL injection
            valid_columns = ['transaction_date', 'post_date', 'description', 'category', 'transaction_type', 'amount']
            if order_by not in valid_columns:
                order_by = 'transaction_date'
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(f"""
                    SELECT * FROM transactions 
                    ORDER BY {order_by} {order_direction}, id DESC
                    LIMIT ? OFFSET ?
                """, (page_size, offset))
                rows = cursor.fetchall()
                
                transactions = []
                for row in rows:
                    transaction = Transaction.from_dict(dict(row))
                    transactions.append(transaction)
                
                return transactions
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve paginated transactions: {e}")
            raise
    
    def search_transactions(self, search_term: str, limit: int = 100) -> List[Transaction]:
        """Search transactions by description, category, or memo with optimized query."""
        try:
            search_pattern = f"%{search_term.lower()}%"
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM transactions 
                    WHERE LOWER(description) LIKE ? 
                       OR LOWER(category) LIKE ? 
                       OR LOWER(memo) LIKE ?
                    ORDER BY transaction_date DESC, id DESC
                    LIMIT ?
                """, (search_pattern, search_pattern, search_pattern, limit))
                rows = cursor.fetchall()
                
                transactions = []
                for row in rows:
                    transaction = Transaction.from_dict(dict(row))
                    transactions.append(transaction)
                
                self.logger.info(f"Found {len(transactions)} transactions matching '{search_term}'")
                return transactions
        except sqlite3.Error as e:
            self.logger.error(f"Failed to search transactions: {e}")
            raise
    
    def get_transactions_by_filters(self, start_date: datetime = None, end_date: datetime = None,
                                  categories: List[str] = None, transaction_types: List[str] = None,
                                  min_amount: float = None, max_amount: float = None,
                                  limit: int = 1000) -> List[Transaction]:
        """Get transactions with multiple filters using optimized query."""
        try:
            query_parts = ["SELECT * FROM transactions WHERE 1=1"]
            params = []
            
            # Date range filter
            if start_date:
                query_parts.append("AND transaction_date >= ?")
                params.append(start_date.isoformat())
            
            if end_date:
                query_parts.append("AND transaction_date <= ?")
                params.append(end_date.isoformat())
            
            # Category filter
            if categories:
                placeholders = ','.join(['?' for _ in categories])
                query_parts.append(f"AND category IN ({placeholders})")
                params.extend(categories)
            
            # Transaction type filter
            if transaction_types:
                placeholders = ','.join(['?' for _ in transaction_types])
                query_parts.append(f"AND transaction_type IN ({placeholders})")
                params.extend(transaction_types)
            
            # Amount range filter
            if min_amount is not None:
                query_parts.append("AND ABS(amount) >= ?")
                params.append(min_amount)
            
            if max_amount is not None:
                query_parts.append("AND ABS(amount) <= ?")
                params.append(max_amount)
            
            # Add ordering and limit
            query_parts.append("ORDER BY transaction_date DESC, id DESC LIMIT ?")
            params.append(limit)
            
            query = " ".join(query_parts)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                transactions = []
                for row in rows:
                    transaction = Transaction.from_dict(dict(row))
                    transactions.append(transaction)
                
                self.logger.info(f"Retrieved {len(transactions)} filtered transactions")
                return transactions
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve filtered transactions: {e}")
            raise
    
    def get_category_stats_optimized(self) -> Dict[str, Dict[str, Any]]:
        """Get category statistics with optimized single query."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        category,
                        COUNT(*) as transaction_count,
                        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses,
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
                        SUM(amount) as net_amount,
                        MIN(transaction_date) as first_transaction,
                        MAX(transaction_date) as last_transaction,
                        AVG(CASE WHEN amount < 0 THEN ABS(amount) ELSE NULL END) as avg_expense,
                        MAX(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as max_expense
                    FROM transactions 
                    GROUP BY category
                    ORDER BY total_expenses DESC
                """)
                
                stats = {}
                for row in cursor.fetchall():
                    stats[row[0]] = {
                        'transaction_count': row[1],
                        'total_expenses': row[2] if row[2] else 0,
                        'total_income': row[3] if row[3] else 0,
                        'net_amount': row[4],
                        'first_transaction': row[5],
                        'last_transaction': row[6],
                        'avg_expense': row[7] if row[7] else 0,
                        'max_expense': row[8] if row[8] else 0
                    }
                
                return stats
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get optimized category stats: {e}")
            raise