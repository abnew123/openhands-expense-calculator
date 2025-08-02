# Local Expense Tracker MVP - Specification

## Purpose
Build a local-first personal finance web application that runs offline, allowing a user to upload credit card transaction CSVs, categorize transactions, filter them by date, and visualize spending by category.

## MVP Features
- Accept CSV uploads in Chase export format
- Parse transactions and store them in SQLite
- Provide a web-based UI to:
    - Display all transactions
    - Edit and save categories per transaction
    - Filter by month and/or year
    - Display simple bar and/or pie charts of spending per category
- App runs entirely locally and offline

## Non-Goals
- No user authentication or accounts
- No cloud sync or remote databases
- No receipt OCR
- No mobile app or deployment beyond local Docker container

## Technology Constraints
- Must be implemented in Python
- Use SQLite for storage
- Prefer Streamlit or Flask
- Use pandas for CSV parsing and data manipulation
- Use Plotly (or equivalent) for data visualization

## Testing Goals
- Include a pytest suite with at least placeholder tests per module
- Include at least one test for each major functionality (CSV parsing, DB insert/read, category update, filtering)

## Deliverables
- Code organized in the provided repository structure
- README.md explaining how to set up and run locally
- Dockerfile that can build and run the app
- Requirements.txt with pinned versions of dependencies

## Repository Structure
openhands-expense-calculator/
├── app/
│   ├── __init__.py           # Package initialization ✅
│   ├── main.py              # Application entry point with logging ✅
│   ├── db.py                # DatabaseManager with SQLite operations ✅
│   ├── models.py            # Transaction dataclass with validation ✅
│   ├── csv_parser.py        # Chase CSV parsing with validation ✅
│   └── views.py             # Streamlit UI components and pages ✅
├── tests/
│   ├── __init__.py
│   └── placeholder_test.py  # Test framework setup
├── llm_notes/              # Development documentation ✅
│   ├── progress/           # PM-style progress updates (6 completed)
│   ├── thinking/           # Developer internal notes
│   └── tickets/            # Jira-style task breakdown (13 tickets)
├── supported_formats/
│   └── chase_download.csv   # Sample Chase CSV format ✅
├── spec.md                 # This specification file
├── requirements.txt        # Pinned dependencies ✅
├── run_app.py             # Streamlit runner script ✅
├── Dockerfile             # Container setup (placeholder)
├── README.md              # Project documentation
├── HANDOFF.md             # Project handoff documentation ✅
├── expenses.db            # SQLite database (auto-created) ✅
├── expense_tracker.log    # Application logs (auto-created) ✅
├── sample_chase_upload.csv # Test CSV file ✅
└── new_transactions.csv   # Additional test data ✅