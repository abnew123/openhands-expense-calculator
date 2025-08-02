import sqlite3
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from app.models import Transaction


class DatabaseManager:
    """Manages SQLite database operations for expense tracking."""
    
    def __init__(self, db_path: str = "expenses.db"):
        """Initialize database manager with specified database path."""
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