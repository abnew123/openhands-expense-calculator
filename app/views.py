import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from app.db import DatabaseManager
from app.csv_parser import CSVParser
from app.models import Transaction


class ExpenseTrackerUI:
    """Main UI class for the expense tracker application."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager()
        self.csv_parser = CSVParser()
        
        # Initialize session state
        if 'transactions' not in st.session_state:
            st.session_state.transactions = []
        if 'filtered_transactions' not in st.session_state:
            st.session_state.filtered_transactions = []
        if 'categories' not in st.session_state:
            st.session_state.categories = []
    
    def run(self):
        """Main application entry point."""
        st.title("💰 Personal Expense Tracker")
        st.markdown("Track and categorize your credit card transactions locally and offline.")
        
        # Sidebar navigation
        page = st.sidebar.selectbox(
            "Navigation",
            ["📊 Dashboard", "📁 Upload CSV", "📋 Transactions", "📈 Analytics"]
        )
        
        # Load data
        self._load_data()
        
        # Route to appropriate page
        if page == "📊 Dashboard":
            self._show_dashboard()
        elif page == "📁 Upload CSV":
            self._show_upload_page()
        elif page == "📋 Transactions":
            self._show_transactions_page()
        elif page == "📈 Analytics":
            self._show_analytics_page()
    
    def _load_data(self):
        """Load transactions and categories from database."""
        try:
            st.session_state.transactions = self.db.get_all_transactions()
            st.session_state.categories = self.db.get_categories()
            st.session_state.filtered_transactions = st.session_state.transactions
        except Exception as e:
            self.logger.error(f"Failed to load data: {e}")
            st.error(f"Failed to load data: {e}")
    
    def _show_dashboard(self):
        """Display the main dashboard with summary statistics."""
        st.header("Dashboard")
        
        if not st.session_state.transactions:
            st.info("No transactions found. Upload a CSV file to get started!")
            return
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_transactions = len(st.session_state.transactions)
        expenses = [t for t in st.session_state.transactions if t.is_expense()]
        payments = [t for t in st.session_state.transactions if t.is_payment()]
        
        total_expenses = sum(abs(t.amount) for t in expenses)
        total_payments = sum(t.amount for t in payments)
        net_amount = sum(t.amount for t in st.session_state.transactions)
        
        with col1:
            st.metric("Total Transactions", total_transactions)
        with col2:
            st.metric("Total Expenses", f"${total_expenses:.2f}")
        with col3:
            st.metric("Total Payments", f"${total_payments:.2f}")
        with col4:
            st.metric("Net Amount", f"${net_amount:.2f}")
        
        # Recent transactions
        st.subheader("Recent Transactions")
        recent_transactions = st.session_state.transactions[:10]
        if recent_transactions:
            df = self._transactions_to_dataframe(recent_transactions)
            st.dataframe(df, use_container_width=True)
        
        # Quick category breakdown
        if expenses:
            st.subheader("Expense Categories")
            category_data = {}
            for t in expenses:
                category_data[t.category] = category_data.get(t.category, 0) + abs(t.amount)
            
            if category_data:
                fig = px.pie(
                    values=list(category_data.values()),
                    names=list(category_data.keys()),
                    title="Spending by Category"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    def _show_upload_page(self):
        """Display the CSV upload page."""
        st.header("Upload CSV File")
        st.markdown("Upload your Chase credit card transaction CSV file to import transactions.")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=['csv'],
            help="Upload a Chase credit card transaction CSV file"
        )
        
        if uploaded_file is not None:
            try:
                # Read file content
                csv_content = uploaded_file.read().decode('utf-8')
                
                # Validate format
                if not self.csv_parser.validate_csv_format(csv_content, "chase"):
                    st.error("Invalid CSV format. Please ensure you're uploading a Chase transaction CSV file.")
                    return
                
                # Show preview
                st.subheader("Preview")
                preview_df = self.csv_parser.get_csv_preview(csv_content)
                st.dataframe(preview_df, use_container_width=True)
                
                # Parse transactions
                transactions = self.csv_parser.parse_chase_csv(csv_content)
                
                if not transactions:
                    st.warning("No valid transactions found in the CSV file.")
                    return
                
                st.success(f"Found {len(transactions)} transactions")
                
                # Check for duplicates
                new_transactions = []
                duplicate_count = 0
                
                for transaction in transactions:
                    if not self.db.transaction_exists(transaction):
                        new_transactions.append(transaction)
                    else:
                        duplicate_count += 1
                
                if duplicate_count > 0:
                    st.warning(f"Found {duplicate_count} duplicate transactions that will be skipped.")
                
                if new_transactions:
                    st.info(f"Ready to import {len(new_transactions)} new transactions.")
                    
                    if st.button("Import Transactions", type="primary"):
                        try:
                            self.db.insert_transactions_batch(new_transactions)
                            st.success(f"Successfully imported {len(new_transactions)} transactions!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to import transactions: {e}")
                else:
                    st.info("All transactions in this file already exist in the database.")
                    
            except Exception as e:
                self.logger.error(f"Upload processing failed: {e}")
                st.error(f"Failed to process uploaded file: {e}")
    
    def _show_transactions_page(self):
        """Display the transactions management page."""
        st.header("Transactions")
        
        if not st.session_state.transactions:
            st.info("No transactions found. Upload a CSV file to get started!")
            return
        
        # Filters
        self._show_filters()
        
        # Transactions table
        if st.session_state.filtered_transactions:
            st.subheader(f"Transactions ({len(st.session_state.filtered_transactions)})")
            self._show_transactions_table()
        else:
            st.info("No transactions match the current filters.")
    
    def _show_analytics_page(self):
        """Display the analytics and charts page."""
        st.header("Analytics")
        
        if not st.session_state.filtered_transactions:
            st.info("No transactions to analyze. Upload data or adjust filters.")
            return
        
        expenses = [t for t in st.session_state.filtered_transactions if t.is_expense()]
        
        if not expenses:
            st.info("No expense transactions found in the current selection.")
            return
        
        # Category breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            self._show_category_pie_chart(expenses)
        
        with col2:
            self._show_category_bar_chart(expenses)
        
        # Spending over time
        self._show_spending_timeline(expenses)
    
    def _show_filters(self):
        """Display filter controls."""
        st.subheader("Filters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range filter
            min_date = min(t.transaction_date for t in st.session_state.transactions).date()
            max_date = max(t.transaction_date for t in st.session_state.transactions).date()
            
            date_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        
        with col2:
            # Category filter
            all_categories = ["All"] + st.session_state.categories
            selected_category = st.selectbox("Category", all_categories)
        
        with col3:
            # Transaction type filter
            transaction_types = ["All", "Expenses Only", "Payments Only"]
            selected_type = st.selectbox("Type", transaction_types)
        
        # Apply filters
        filtered = st.session_state.transactions
        
        # Date filter
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered = [t for t in filtered 
                       if start_date <= t.transaction_date.date() <= end_date]
        
        # Category filter
        if selected_category != "All":
            filtered = [t for t in filtered if t.category == selected_category]
        
        # Type filter
        if selected_type == "Expenses Only":
            filtered = [t for t in filtered if t.is_expense()]
        elif selected_type == "Payments Only":
            filtered = [t for t in filtered if t.is_payment()]
        
        st.session_state.filtered_transactions = filtered
    
    def _show_transactions_table(self):
        """Display transactions in an editable table."""
        df = self._transactions_to_dataframe(st.session_state.filtered_transactions)
        
        # Display the dataframe
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "Amount": st.column_config.NumberColumn(
                    "Amount",
                    format="$%.2f"
                ),
                "Date": st.column_config.DateColumn(
                    "Date",
                    format="YYYY-MM-DD"
                )
            }
        )
        
        # Category editing section
        st.subheader("Edit Categories")
        
        if st.session_state.filtered_transactions:
            # Select transaction to edit
            transaction_options = [
                f"{t.transaction_date.strftime('%Y-%m-%d')} - {t.description[:50]} - ${t.amount:.2f}"
                for t in st.session_state.filtered_transactions
            ]
            
            selected_idx = st.selectbox(
                "Select transaction to edit",
                range(len(transaction_options)),
                format_func=lambda x: transaction_options[x]
            )
            
            if selected_idx is not None:
                selected_transaction = st.session_state.filtered_transactions[selected_idx]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Current Category:** {selected_transaction.category}")
                
                with col2:
                    # Category selection
                    all_categories = st.session_state.categories + ["Create New..."]
                    
                    if selected_transaction.category in all_categories:
                        default_idx = all_categories.index(selected_transaction.category)
                    else:
                        default_idx = 0
                    
                    new_category = st.selectbox(
                        "New Category",
                        all_categories,
                        index=default_idx,
                        key=f"category_select_{selected_transaction.id}"
                    )
                    
                    # Handle new category creation
                    if new_category == "Create New...":
                        new_category = st.text_input("Enter new category name")
                    
                    if new_category and new_category != "Create New..." and new_category != selected_transaction.category:
                        if st.button("Update Category", type="primary"):
                            try:
                                success = self.db.update_transaction_category(selected_transaction.id, new_category)
                                if success:
                                    st.success(f"Updated category to '{new_category}'")
                                    st.rerun()
                                else:
                                    st.error("Failed to update category")
                            except Exception as e:
                                st.error(f"Error updating category: {e}")
    
    def _transactions_to_dataframe(self, transactions: List[Transaction]) -> pd.DataFrame:
        """Convert transactions to pandas DataFrame for display."""
        if not transactions:
            return pd.DataFrame()
        
        data = []
        for t in transactions:
            data.append({
                'Date': t.transaction_date.date(),
                'Description': t.description,
                'Category': t.category,
                'Type': t.transaction_type,
                'Amount': float(t.amount),
                'Memo': t.memo or ""
            })
        
        return pd.DataFrame(data)
    
    def _show_category_pie_chart(self, expenses: List[Transaction]):
        """Display pie chart of expenses by category."""
        category_totals = {}
        for t in expenses:
            category_totals[t.category] = category_totals.get(t.category, 0) + abs(t.amount)
        
        if category_totals:
            fig = px.pie(
                values=list(category_totals.values()),
                names=list(category_totals.keys()),
                title="Expenses by Category (Pie Chart)"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    def _show_category_bar_chart(self, expenses: List[Transaction]):
        """Display bar chart of expenses by category."""
        category_totals = {}
        for t in expenses:
            category_totals[t.category] = category_totals.get(t.category, 0) + abs(t.amount)
        
        if category_totals:
            fig = px.bar(
                x=list(category_totals.keys()),
                y=list(category_totals.values()),
                title="Expenses by Category (Bar Chart)",
                labels={'x': 'Category', 'y': 'Amount ($)'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    def _show_spending_timeline(self, expenses: List[Transaction]):
        """Display spending timeline chart."""
        if not expenses:
            return
        
        # Group by month
        monthly_spending = {}
        for t in expenses:
            month_key = t.transaction_date.strftime('%Y-%m')
            monthly_spending[month_key] = monthly_spending.get(month_key, 0) + abs(t.amount)
        
        if monthly_spending:
            months = sorted(monthly_spending.keys())
            amounts = [monthly_spending[month] for month in months]
            
            fig = px.line(
                x=months,
                y=amounts,
                title="Monthly Spending Trend",
                labels={'x': 'Month', 'y': 'Amount ($)'}
            )
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)