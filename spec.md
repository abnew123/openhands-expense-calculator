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
expense-tracker/
├── app/
│   ├── __init__.py
│   ├── main.py              # entry point
│   ├── db.py                # sqlite helpers
│   ├── models.py            # define transaction object
│   ├── views.py             # streamlit/flask UI
│   └── static/              # CSS/images
├── tests/
│   └── test_placeholder.py
├── spec.md
├── requirements.txt
├── Dockerfile
├── README.md
├── llm_notes/
│   ├── progress              # stores current state
│   ├── thinking              # stores thoughts
│   ├── tickets               # stores goals
├── supported_formats/        # one file per supported format