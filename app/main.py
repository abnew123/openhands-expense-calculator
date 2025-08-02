import streamlit as st
import logging
from pathlib import Path

from app.views import ExpenseTrackerUI


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('expense_tracker.log')
        ]
    )


def main():
    """Main entry point for the Streamlit application."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Configure Streamlit page
    st.set_page_config(
        page_title="Expense Tracker",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize and run the UI
    try:
        ui = ExpenseTrackerUI()
        ui.run()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"An error occurred: {e}")
        st.error("Please check the logs for more details.")


if __name__ == "__main__":
    main()