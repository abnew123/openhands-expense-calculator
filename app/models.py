from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Transaction:
    """Represents a financial transaction from a credit card statement."""
    
    transaction_date: datetime
    post_date: datetime
    description: str
    category: str
    transaction_type: str
    amount: Decimal
    memo: Optional[str] = None
    id: Optional[int] = None  # Database ID, set after insertion
    
    def __post_init__(self):
        """Validate transaction data after initialization."""
        if not self.description.strip():
            raise ValueError("Description cannot be empty")
        
        if not self.category.strip():
            self.category = "Uncategorized"
            
        if self.amount == 0:
            raise ValueError("Amount cannot be zero")
    
    def to_dict(self) -> dict:
        """Convert transaction to dictionary for database operations."""
        return {
            'id': self.id,
            'transaction_date': self.transaction_date.isoformat(),
            'post_date': self.post_date.isoformat(),
            'description': self.description,
            'category': self.category,
            'transaction_type': self.transaction_type,
            'amount': float(self.amount),
            'memo': self.memo
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        """Create transaction from dictionary (e.g., from database)."""
        return cls(
            id=data.get('id'),
            transaction_date=datetime.fromisoformat(data['transaction_date']),
            post_date=datetime.fromisoformat(data['post_date']),
            description=data['description'],
            category=data['category'],
            transaction_type=data['transaction_type'],
            amount=Decimal(str(data['amount'])),
            memo=data.get('memo')
        )
    
    def is_expense(self) -> bool:
        """Check if this transaction is an expense (negative amount)."""
        return self.amount < 0
    
    def is_payment(self) -> bool:
        """Check if this transaction is a payment (positive amount)."""
        return self.amount > 0
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.transaction_date.strftime('%Y-%m-%d')}: {self.description} - ${self.amount:.2f} ({self.category})"
    
    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (f"Transaction(id={self.id}, date={self.transaction_date.date()}, "
                f"description='{self.description}', amount={self.amount}, category='{self.category}')")