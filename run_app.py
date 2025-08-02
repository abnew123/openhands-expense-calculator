#!/usr/bin/env python3
"""
Entry point for the Expense Tracker Streamlit application.
Run with: streamlit run run_app.py
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.main import main

if __name__ == "__main__":
    main()