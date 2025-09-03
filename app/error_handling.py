"""Enhanced error handling and user feedback utilities."""

import logging
import traceback
from typing import Any, Callable, Optional, Dict
from functools import wraps
import streamlit as st


class ErrorHandler:
    """Centralized error handling with user-friendly messages."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def handle_database_error(self, error: Exception, operation: str) -> None:
        """Handle database-related errors with specific guidance."""
        error_msg = str(error).lower()
        
        if "database is locked" in error_msg:
            st.error("🔒 Database is currently locked")
            st.info("**Solution:** Please wait a moment and try again. If the problem persists, restart the application.")
        
        elif "no such table" in error_msg:
            st.error("🗃️ Database table not found")
            st.info("**Solution:** The database may be corrupted. Try restarting the application to recreate the database.")
            
            if st.button("🔄 Recreate Database", key="recreate_db"):
                st.warning("This will create a new empty database. All existing data will be lost.")
        
        elif "disk i/o error" in error_msg or "disk full" in error_msg:
            st.error("💾 Disk storage issue")
            st.info("**Solution:** Check available disk space and ensure the application has write permissions.")
        
        elif "constraint" in error_msg:
            st.error("⚠️ Data validation error")
            st.info("**Solution:** The data doesn't meet database requirements. Please check your input and try again.")
        
        else:
            st.error(f"🗃️ Database error during {operation}")
            st.info("**Solution:** Please try again. If the problem persists, check the application logs.")
        
        # Log technical details
        self.logger.error(f"Database error in {operation}: {error}")
        
        # Show technical details in expander
        with st.expander("🔧 Technical Details"):
            st.code(str(error))
    
    def handle_csv_error(self, error: Exception, filename: str = "") -> None:
        """Handle CSV processing errors with specific guidance."""
        error_msg = str(error).lower()
        
        if "no columns to parse" in error_msg or "empty" in error_msg:
            st.error("📄 Empty or invalid CSV file")
            st.info("**Solution:** Please ensure your CSV file contains data and has the correct format.")
        
        elif "missing required columns" in error_msg:
            st.error("📋 CSV format mismatch")
            st.info("**Required columns:** Transaction Date, Post Date, Description, Category, Type, Amount, Memo")
            st.info("**Solution:** Please use a Chase credit card CSV export file.")
        
        elif "date" in error_msg and "parse" in error_msg:
            st.error("📅 Date format error")
            st.info("**Solution:** Ensure dates are in MM/DD/YYYY format (e.g., 01/15/2024).")
        
        elif "amount" in error_msg or "float" in error_msg:
            st.error("💰 Amount format error")
            st.info("**Solution:** Ensure amounts are numeric values (e.g., -25.99, 150.00).")
        
        else:
            st.error(f"📄 CSV processing error{' for ' + filename if filename else ''}")
            st.info("**Solution:** Please check your CSV file format and try again.")
        
        # Log technical details
        self.logger.error(f"CSV error for {filename}: {error}")
        
        # Show technical details in expander
        with st.expander("🔧 Technical Details"):
            st.code(str(error))
    
    def handle_import_export_error(self, error: Exception, operation: str) -> None:
        """Handle import/export errors with specific guidance."""
        error_msg = str(error).lower()
        
        if "json" in error_msg and "decode" in error_msg:
            st.error("📄 Invalid JSON format")
            st.info("**Solution:** Please ensure you're uploading a valid JSON export file from this application.")
        
        elif "permission" in error_msg or "access" in error_msg:
            st.error("🔐 File access error")
            st.info("**Solution:** Check file permissions and ensure the file is not open in another application.")
        
        elif "memory" in error_msg or "size" in error_msg:
            st.error("💾 File too large")
            st.info("**Solution:** The file may be too large to process. Try exporting smaller date ranges.")
        
        else:
            st.error(f"📁 {operation} error")
            st.info("**Solution:** Please check your file and try again.")
        
        # Log technical details
        self.logger.error(f"{operation} error: {error}")
        
        # Show technical details in expander
        with st.expander("🔧 Technical Details"):
            st.code(str(error))
    
    def handle_general_error(self, error: Exception, operation: str) -> None:
        """Handle general application errors."""
        st.error(f"❌ Error during {operation}")
        st.info("**Solution:** Please try again. If the problem persists, restart the application.")
        
        # Log technical details
        self.logger.error(f"General error in {operation}: {error}")
        self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Show technical details in expander
        with st.expander("🔧 Technical Details"):
            st.code(str(error))
            st.code(traceback.format_exc())


# Global error handler instance
error_handler = ErrorHandler()


def safe_operation(operation_name: str, show_spinner: bool = True):
    """Decorator for safe operation execution with error handling."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                if show_spinner:
                    with st.spinner(f"Processing {operation_name}..."):
                        return func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                # Determine error type and handle appropriately
                error_msg = str(e).lower()
                
                if "database" in error_msg or "sqlite" in error_msg:
                    error_handler.handle_database_error(e, operation_name)
                elif "csv" in error_msg or "parse" in error_msg:
                    error_handler.handle_csv_error(e)
                elif "json" in error_msg or "export" in error_msg or "import" in error_msg:
                    error_handler.handle_import_export_error(e, operation_name)
                else:
                    error_handler.handle_general_error(e, operation_name)
                
                return None
        return wrapper
    return decorator


class ProgressTracker:
    """Track and display progress for long-running operations."""
    
    def __init__(self, total_steps: int, operation_name: str):
        self.total_steps = total_steps
        self.current_step = 0
        self.operation_name = operation_name
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.logger = logging.getLogger(__name__)
    
    def update(self, step: int, message: str = ""):
        """Update progress bar and status message."""
        self.current_step = step
        progress = min(step / self.total_steps, 1.0)
        
        self.progress_bar.progress(progress)
        
        if message:
            self.status_text.text(f"{self.operation_name}: {message}")
        else:
            self.status_text.text(f"{self.operation_name}: Step {step} of {self.total_steps}")
        
        self.logger.info(f"{self.operation_name} progress: {step}/{self.total_steps} - {message}")
    
    def complete(self, success_message: str = ""):
        """Mark operation as complete."""
        self.progress_bar.progress(1.0)
        
        if success_message:
            self.status_text.success(success_message)
        else:
            self.status_text.success(f"{self.operation_name} completed successfully!")
        
        self.logger.info(f"{self.operation_name} completed")
    
    def error(self, error_message: str):
        """Mark operation as failed."""
        self.status_text.error(f"{self.operation_name} failed: {error_message}")
        self.logger.error(f"{self.operation_name} failed: {error_message}")


def show_success_message(message: str, details: str = ""):
    """Show a success message with optional details."""
    st.success(f"✅ {message}")
    if details:
        st.info(details)


def show_warning_message(message: str, details: str = ""):
    """Show a warning message with optional details."""
    st.warning(f"⚠️ {message}")
    if details:
        st.info(details)


def show_info_message(message: str, details: str = ""):
    """Show an info message with optional details."""
    st.info(f"ℹ️ {message}")
    if details:
        st.write(details)


def validate_user_input(input_value: Any, input_type: str, field_name: str) -> bool:
    """Validate user input and show appropriate feedback."""
    if input_type == "required_text":
        if not input_value or not str(input_value).strip():
            st.error(f"❌ {field_name} is required")
            return False
    
    elif input_type == "positive_number":
        try:
            num_value = float(input_value)
            if num_value <= 0:
                st.error(f"❌ {field_name} must be a positive number")
                return False
        except (ValueError, TypeError):
            st.error(f"❌ {field_name} must be a valid number")
            return False
    
    elif input_type == "date":
        if not input_value:
            st.error(f"❌ {field_name} is required")
            return False
    
    return True


def create_retry_button(operation_name: str, retry_key: str) -> bool:
    """Create a retry button for failed operations."""
    return st.button(f"🔄 Retry {operation_name}", key=retry_key)