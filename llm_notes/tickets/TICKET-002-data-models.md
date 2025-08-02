# TICKET-002: Create Data Models

## Status: COMPLETED

## Description
Define the Transaction data model and related classes to represent expense data in the application.

## Acceptance Criteria
- [x] Create Transaction class in models.py with fields:
  - transaction_date (date)
  - post_date (date)
  - description (string)
  - category (string, editable)
  - transaction_type (string)
  - amount (decimal)
  - memo (string, optional)
- [x] Add validation methods for data integrity
- [x] Include methods for converting to/from dict for database operations
- [x] Add __str__ and __repr__ methods for debugging

## Dependencies
- TICKET-001 (dependencies needed for dataclass/pydantic)

## Estimated Effort
Small (2-3 hours)

## Notes
- Consider using dataclasses or pydantic for validation
- Amount should handle negative values for expenses vs positive for payments
- Category should be editable and default to "Uncategorized"