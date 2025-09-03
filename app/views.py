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
            ["📊 Dashboard", "📁 Upload CSV", "📋 Transactions", "📈 Analytics", "🏷️ Categories"]
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
        elif page == "🏷️ Categories":
            self._show_categories_page()
    
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
        
        # Show filters
        self._show_filters()
        
        # Use filtered transactions for dashboard metrics
        transactions_to_show = st.session_state.filtered_transactions
        
        if not transactions_to_show:
            st.warning("No transactions match the current filters.")
            return
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_transactions = len(transactions_to_show)
        expenses = [t for t in transactions_to_show if t.is_expense()]
        payments = [t for t in transactions_to_show if t.is_payment()]
        
        total_expenses = sum(abs(t.amount) for t in expenses)
        total_payments = sum(t.amount for t in payments)
        net_amount = sum(t.amount for t in transactions_to_show)
        
        with col1:
            st.metric("Transactions", total_transactions)
        with col2:
            st.metric("Total Expenses", f"${total_expenses:.2f}")
        with col3:
            st.metric("Total Payments", f"${total_payments:.2f}")
        with col4:
            st.metric("Net Amount", f"${net_amount:.2f}")
        
        # Additional metrics row
        if expenses:
            col1, col2, col3, col4 = st.columns(4)
            
            avg_expense = total_expenses / len(expenses) if expenses else 0
            max_expense = max(abs(t.amount) for t in expenses) if expenses else 0
            expense_categories = len(set(t.category for t in expenses))
            
            with col1:
                st.metric("Avg Expense", f"${avg_expense:.2f}")
            with col2:
                st.metric("Largest Expense", f"${max_expense:.2f}")
            with col3:
                st.metric("Categories", expense_categories)
            with col4:
                if len(transactions_to_show) > 0:
                    date_range_days = (max(t.transaction_date for t in transactions_to_show) - 
                                     min(t.transaction_date for t in transactions_to_show)).days + 1
                    st.metric("Date Range", f"{date_range_days} days")
        
        # Recent transactions
        st.subheader("Recent Transactions")
        recent_transactions = sorted(transactions_to_show, key=lambda t: t.transaction_date, reverse=True)[:10]
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
                # Sort categories by amount
                sorted_categories = sorted(category_data.items(), key=lambda x: x[1], reverse=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.pie(
                        values=[item[1] for item in sorted_categories],
                        names=[item[0] for item in sorted_categories],
                        title="Spending by Category"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Top categories table
                    st.write("**Top Categories**")
                    top_categories = sorted_categories[:8]
                    for category, amount in top_categories:
                        percentage = (amount / total_expenses) * 100
                        st.write(f"• **{category}**: ${amount:.2f} ({percentage:.1f}%)")
        
        # Monthly spending trend (if data spans multiple months)
        if expenses and len(transactions_to_show) > 0:
            date_range_days = (max(t.transaction_date for t in transactions_to_show) - 
                             min(t.transaction_date for t in transactions_to_show)).days
            
            if date_range_days > 30:  # Show trend if more than 30 days of data
                st.subheader("Spending Trend")
                self._show_spending_timeline(expenses)
    
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
        """Display enhanced filter controls with date presets."""
        with st.expander("🔍 Filters", expanded=True):
            # Get date bounds from transactions
            min_date = min(t.transaction_date for t in st.session_state.transactions).date()
            max_date = max(t.transaction_date for t in st.session_state.transactions).date()
            
            # Date filtering section
            st.write("**📅 Date Range**")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Date presets
                date_preset = st.selectbox(
                    "Quick Select",
                    [
                        "Custom Range",
                        "All Time",
                        "This Month",
                        "Last Month", 
                        "Last 3 Months",
                        "Last 6 Months",
                        "This Year",
                        "Last Year",
                        "Last 30 Days",
                        "Last 90 Days"
                    ],
                    key="date_preset"
                )
            
            with col2:
                # Calculate date range based on preset
                today = datetime.now().date()
                
                if date_preset == "All Time":
                    start_date, end_date = min_date, max_date
                elif date_preset == "This Month":
                    start_date = today.replace(day=1)
                    end_date = today
                elif date_preset == "Last Month":
                    if today.month == 1:
                        start_date = today.replace(year=today.year-1, month=12, day=1)
                        end_date = today.replace(day=1) - timedelta(days=1)
                    else:
                        start_date = today.replace(month=today.month-1, day=1)
                        if today.month == 1:
                            end_date = today.replace(year=today.year-1, month=12, day=31)
                        else:
                            next_month = today.replace(month=today.month, day=1)
                            end_date = next_month - timedelta(days=1)
                elif date_preset == "Last 3 Months":
                    end_date = today
                    start_date = (today - timedelta(days=90)).replace(day=1)
                elif date_preset == "Last 6 Months":
                    end_date = today
                    start_date = (today - timedelta(days=180)).replace(day=1)
                elif date_preset == "This Year":
                    start_date = today.replace(month=1, day=1)
                    end_date = today
                elif date_preset == "Last Year":
                    start_date = today.replace(year=today.year-1, month=1, day=1)
                    end_date = today.replace(year=today.year-1, month=12, day=31)
                elif date_preset == "Last 30 Days":
                    end_date = today
                    start_date = today - timedelta(days=30)
                elif date_preset == "Last 90 Days":
                    end_date = today
                    start_date = today - timedelta(days=90)
                else:  # Custom Range
                    # Use session state to maintain custom range
                    if 'custom_date_range' not in st.session_state:
                        st.session_state.custom_date_range = (min_date, max_date)
                    
                    custom_range = st.date_input(
                        "Custom Date Range",
                        value=st.session_state.custom_date_range,
                        min_value=min_date,
                        max_value=max_date,
                        key="custom_date_input"
                    )
                    
                    if isinstance(custom_range, tuple) and len(custom_range) == 2:
                        start_date, end_date = custom_range
                        st.session_state.custom_date_range = custom_range
                    else:
                        start_date, end_date = min_date, max_date
                
                # Ensure dates are within bounds
                start_date = max(start_date, min_date)
                end_date = min(end_date, max_date)
                
                if date_preset != "Custom Range":
                    st.write(f"**Selected Range:** {start_date} to {end_date}")
            
            # Other filters
            st.write("**🏷️ Category & Type Filters**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Category filter
                all_categories = ["All"] + st.session_state.categories
                selected_category = st.selectbox("Category", all_categories, key="category_filter")
            
            with col2:
                # Transaction type filter
                transaction_types = ["All", "Expenses Only", "Payments Only"]
                selected_type = st.selectbox("Type", transaction_types, key="type_filter")
            
            with col3:
                # Amount range filter
                if st.session_state.transactions:
                    amounts = [abs(t.amount) for t in st.session_state.transactions]
                    min_amount, max_amount = min(amounts), max(amounts)
                    
                    amount_range = st.slider(
                        "Amount Range ($)",
                        min_value=0.0,
                        max_value=float(max_amount),
                        value=(0.0, float(max_amount)),
                        step=1.0,
                        key="amount_filter"
                    )
            
            # Apply filters
            filtered = st.session_state.transactions
            
            # Date filter
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
            
            # Amount filter
            if st.session_state.transactions:
                min_amt, max_amt = amount_range
                filtered = [t for t in filtered if min_amt <= abs(t.amount) <= max_amt]
            
            st.session_state.filtered_transactions = filtered
            
            # Show filter summary
            total_transactions = len(st.session_state.transactions)
            filtered_count = len(filtered)
            
            if filtered_count < total_transactions:
                st.info(f"Showing {filtered_count} of {total_transactions} transactions")
                
                # Quick filter reset
                if st.button("🔄 Reset All Filters", key="reset_filters"):
                    # Reset session state filter values
                    if 'date_preset' in st.session_state:
                        st.session_state.date_preset = "All Time"
                    if 'category_filter' in st.session_state:
                        st.session_state.category_filter = "All"
                    if 'type_filter' in st.session_state:
                        st.session_state.type_filter = "All"
                    st.rerun()
            else:
                st.success(f"Showing all {total_transactions} transactions")
    
    def _show_transactions_table(self):
        """Display transactions in an enhanced table with search and sorting."""
        transactions = st.session_state.filtered_transactions
        
        # Search functionality
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_term = st.text_input(
                "🔍 Search transactions",
                placeholder="Search by description, category, or memo...",
                key="transaction_search"
            )
        
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                ["Date (Newest)", "Date (Oldest)", "Amount (High to Low)", "Amount (Low to High)", "Description", "Category"],
                key="transaction_sort"
            )
        
        with col3:
            page_size = st.selectbox(
                "Show",
                [25, 50, 100, "All"],
                index=0,
                key="transaction_page_size"
            )
        
        # Apply search filter
        if search_term:
            search_lower = search_term.lower()
            transactions = [
                t for t in transactions
                if (search_lower in t.description.lower() or
                    search_lower in t.category.lower() or
                    (t.memo and search_lower in t.memo.lower()))
            ]
        
        # Apply sorting
        if sort_by == "Date (Newest)":
            transactions.sort(key=lambda t: t.transaction_date, reverse=True)
        elif sort_by == "Date (Oldest)":
            transactions.sort(key=lambda t: t.transaction_date)
        elif sort_by == "Amount (High to Low)":
            transactions.sort(key=lambda t: abs(t.amount), reverse=True)
        elif sort_by == "Amount (Low to High)":
            transactions.sort(key=lambda t: abs(t.amount))
        elif sort_by == "Description":
            transactions.sort(key=lambda t: t.description.lower())
        elif sort_by == "Category":
            transactions.sort(key=lambda t: t.category.lower())
        
        # Pagination
        total_transactions = len(transactions)
        
        if page_size != "All":
            page_size = int(page_size)
            
            # Initialize page number in session state
            if 'current_page' not in st.session_state:
                st.session_state.current_page = 0
            
            total_pages = (total_transactions + page_size - 1) // page_size
            
            if total_pages > 1:
                col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
                
                with col1:
                    if st.button("⏮️ First", disabled=st.session_state.current_page == 0):
                        st.session_state.current_page = 0
                        st.rerun()
                
                with col2:
                    if st.button("◀️ Prev", disabled=st.session_state.current_page == 0):
                        st.session_state.current_page -= 1
                        st.rerun()
                
                with col3:
                    st.write(f"Page {st.session_state.current_page + 1} of {total_pages} ({total_transactions} total)")
                
                with col4:
                    if st.button("Next ▶️", disabled=st.session_state.current_page >= total_pages - 1):
                        st.session_state.current_page += 1
                        st.rerun()
                
                with col5:
                    if st.button("Last ⏭️", disabled=st.session_state.current_page >= total_pages - 1):
                        st.session_state.current_page = total_pages - 1
                        st.rerun()
            
            # Reset page if it's out of bounds
            if st.session_state.current_page >= total_pages:
                st.session_state.current_page = max(0, total_pages - 1)
            
            # Get transactions for current page
            start_idx = st.session_state.current_page * page_size
            end_idx = min(start_idx + page_size, total_transactions)
            transactions = transactions[start_idx:end_idx]
        
        # Convert to DataFrame and display
        df = self._transactions_to_dataframe(transactions)
        
        if not df.empty:
            # Display the dataframe with enhanced formatting
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
                    ),
                    "Description": st.column_config.TextColumn(
                        "Description",
                        width="large"
                    ),
                    "Category": st.column_config.TextColumn(
                        "Category",
                        width="medium"
                    ),
                    "Type": st.column_config.TextColumn(
                        "Type",
                        width="small"
                    )
                },
                hide_index=True
            )
        else:
            st.info("No transactions match your search criteria.")
        
        # Category editing section
        if transactions:
            with st.expander("🏷️ Edit Categories", expanded=False):
                tab1, tab2 = st.tabs(["Single Transaction", "Bulk Edit"])
                
                with tab1:
                    self._show_single_category_edit(transactions)
                
                with tab2:
                    self._show_bulk_category_edit(transactions)
    
    def _show_single_category_edit(self, transactions: List[Transaction]):
        """Show single transaction category editing interface."""
        if not transactions:
            st.info("No transactions available for editing.")
            return
        
        # Select transaction to edit
        transaction_options = [
            f"{t.transaction_date.strftime('%Y-%m-%d')} - {t.description[:50]} - ${t.amount:.2f}"
            for t in transactions
        ]
        
        selected_idx = st.selectbox(
            "Select transaction to edit",
            range(len(transaction_options)),
            format_func=lambda x: transaction_options[x],
            key="single_edit_select"
        )
        
        if selected_idx is not None:
            selected_transaction = transactions[selected_idx]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Current Category:** {selected_transaction.category}")
                st.write(f"**Description:** {selected_transaction.description}")
                st.write(f"**Amount:** ${selected_transaction.amount:.2f}")
            
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
                    key="single_category_select"
                )
                
                # Handle new category creation
                if new_category == "Create New...":
                    new_category = st.text_input("Enter new category name", key="single_new_category")
                
                if new_category and new_category != "Create New..." and new_category != selected_transaction.category:
                    if st.button("Update Category", type="primary", key="single_update"):
                        try:
                            success = self.db.update_transaction_category(selected_transaction.id, new_category)
                            if success:
                                st.success(f"Updated category to '{new_category}'")
                                st.rerun()
                            else:
                                st.error("Failed to update category")
                        except Exception as e:
                            st.error(f"Error updating category: {e}")
    
    def _show_bulk_category_edit(self, transactions: List[Transaction]):
        """Show bulk category editing interface."""
        if not transactions:
            st.info("No transactions available for bulk editing.")
            return
        
        st.write("**Bulk Category Update**")
        st.write("Update multiple transactions at once based on description patterns or current categories.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            bulk_method = st.radio(
                "Bulk edit method",
                ["By Description Pattern", "By Current Category"],
                key="bulk_method"
            )
        
        with col2:
            if bulk_method == "By Description Pattern":
                pattern = st.text_input(
                    "Description contains (case-insensitive)",
                    placeholder="e.g., 'AMAZON', 'STARBUCKS'",
                    key="bulk_pattern"
                )
                
                if pattern:
                    matching_transactions = [
                        t for t in transactions
                        if pattern.lower() in t.description.lower()
                    ]
                    st.write(f"Found {len(matching_transactions)} matching transactions")
                    
                    if matching_transactions:
                        # Show preview of matching transactions
                        preview_df = self._transactions_to_dataframe(matching_transactions[:5])
                        st.write("Preview (showing first 5):")
                        st.dataframe(preview_df, use_container_width=True)
                        
                        if len(matching_transactions) > 5:
                            st.write(f"... and {len(matching_transactions) - 5} more")
            
            else:  # By Current Category
                current_categories = list(set(t.category for t in transactions))
                selected_category = st.selectbox(
                    "Current category to update",
                    current_categories,
                    key="bulk_current_category"
                )
                
                if selected_category:
                    matching_transactions = [
                        t for t in transactions
                        if t.category == selected_category
                    ]
                    st.write(f"Found {len(matching_transactions)} transactions with category '{selected_category}'")
        
        # New category selection for bulk update
        if ((bulk_method == "By Description Pattern" and pattern and matching_transactions) or
            (bulk_method == "By Current Category" and selected_category and matching_transactions)):
            
            st.write("**Select new category:**")
            all_categories = st.session_state.categories + ["Create New..."]
            
            new_bulk_category = st.selectbox(
                "New category for selected transactions",
                all_categories,
                key="bulk_new_category"
            )
            
            if new_bulk_category == "Create New...":
                new_bulk_category = st.text_input("Enter new category name", key="bulk_create_category")
            
            if new_bulk_category and new_bulk_category != "Create New...":
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Transactions to update:** {len(matching_transactions)}")
                    st.write(f"**New category:** {new_bulk_category}")
                
                with col2:
                    if st.button("Update All Selected", type="primary", key="bulk_update"):
                        try:
                            updated_count = 0
                            for transaction in matching_transactions:
                                if self.db.update_transaction_category(transaction.id, new_bulk_category):
                                    updated_count += 1
                            
                            if updated_count > 0:
                                st.success(f"Successfully updated {updated_count} transactions to category '{new_bulk_category}'")
                                st.rerun()
                            else:
                                st.error("Failed to update any transactions")
                        except Exception as e:
                            st.error(f"Error during bulk update: {e}")
    
    def _transactions_to_dataframe(self, transactions: List[Transaction]) -> pd.DataFrame:
        """Convert transactions to pandas DataFrame for display."""
        if not transactions:
            return pd.DataFrame()
        
        data = []
        for t in transactions:
            # Format amount with proper sign and color indication
            amount_display = float(t.amount)
            
            data.append({
                'Date': t.transaction_date.date(),
                'Description': t.description[:60] + ('...' if len(t.description) > 60 else ''),
                'Category': t.category,
                'Type': t.transaction_type,
                'Amount': amount_display,
                'Memo': (t.memo[:30] + '...' if t.memo and len(t.memo) > 30 else t.memo) or ""
            })
        
        df = pd.DataFrame(data)
        
        # Reorder columns for better display
        column_order = ['Date', 'Description', 'Category', 'Type', 'Amount', 'Memo']
        df = df[column_order]
        
        return df
    
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
    
    def _show_categories_page(self):
        """Display the category management page."""
        st.header("Category Management")
        st.markdown("Manage your transaction categories: view statistics, rename, merge, or delete categories.")
        
        if not st.session_state.transactions:
            st.info("No transactions found. Upload data to manage categories.")
            return
        
        # Get category statistics
        try:
            category_stats = self.db.get_category_stats()
        except Exception as e:
            st.error(f"Failed to load category statistics: {e}")
            return
        
        if not category_stats:
            st.info("No categories found.")
            return
        
        # Category overview
        st.subheader("📊 Category Overview")
        
        # Create overview dataframe
        overview_data = []
        for category, stats in category_stats.items():
            overview_data.append({
                'Category': category,
                'Transactions': stats['transaction_count'],
                'Total Expenses': f"${stats['total_expenses']:.2f}",
                'Total Income': f"${stats['total_income']:.2f}",
                'Net Amount': f"${stats['net_amount']:.2f}",
                'First Transaction': stats['first_transaction'][:10] if stats['first_transaction'] else 'N/A',
                'Last Transaction': stats['last_transaction'][:10] if stats['last_transaction'] else 'N/A'
            })
        
        overview_df = pd.DataFrame(overview_data)
        st.dataframe(overview_df, use_container_width=True)
        
        # Category management actions
        st.subheader("🛠️ Category Actions")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Rename Category", "Merge Categories", "Delete Category", "Auto-Categorize"])
        
        with tab1:
            self._show_rename_category_tab(category_stats)
        
        with tab2:
            self._show_merge_categories_tab(category_stats)
        
        with tab3:
            self._show_delete_category_tab(category_stats)
        
        with tab4:
            self._show_auto_categorize_tab()
    
    def _show_rename_category_tab(self, category_stats):
        """Show the rename category interface."""
        st.write("**Rename a category across all transactions**")
        
        categories = list(category_stats.keys())
        
        col1, col2 = st.columns(2)
        
        with col1:
            old_category = st.selectbox(
                "Select category to rename",
                categories,
                key="rename_old_category"
            )
            
            if old_category:
                stats = category_stats[old_category]
                st.info(f"This category has {stats['transaction_count']} transactions")
        
        with col2:
            new_category = st.text_input(
                "New category name",
                key="rename_new_category"
            )
        
        if old_category and new_category and new_category != old_category:
            if new_category in categories:
                st.warning(f"Category '{new_category}' already exists. This will merge the categories.")
            
            if st.button("Rename Category", type="primary", key="rename_button"):
                try:
                    updated_count = self.db.rename_category(old_category, new_category)
                    st.success(f"Successfully renamed '{old_category}' to '{new_category}' for {updated_count} transactions")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to rename category: {e}")
    
    def _show_merge_categories_tab(self, category_stats):
        """Show the merge categories interface."""
        st.write("**Merge multiple categories into one**")
        
        categories = list(category_stats.keys())
        
        col1, col2 = st.columns(2)
        
        with col1:
            categories_to_merge = st.multiselect(
                "Select categories to merge",
                categories,
                key="merge_source_categories"
            )
            
            if categories_to_merge:
                total_transactions = sum(category_stats[cat]['transaction_count'] for cat in categories_to_merge)
                st.info(f"Selected categories have {total_transactions} total transactions")
        
        with col2:
            target_category = st.selectbox(
                "Target category (or create new)",
                ["Create New..."] + categories,
                key="merge_target_category"
            )
            
            if target_category == "Create New...":
                target_category = st.text_input("New category name", key="merge_new_category")
        
        if categories_to_merge and target_category and target_category != "Create New...":
            if target_category in categories_to_merge:
                st.error("Target category cannot be one of the categories being merged")
            else:
                if st.button("Merge Categories", type="primary", key="merge_button"):
                    try:
                        updated_count = self.db.merge_categories(categories_to_merge, target_category)
                        st.success(f"Successfully merged {len(categories_to_merge)} categories into '{target_category}' for {updated_count} transactions")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to merge categories: {e}")
    
    def _show_delete_category_tab(self, category_stats):
        """Show the delete category interface."""
        st.write("**Delete a category (transactions will be moved to replacement category)**")
        
        categories = list(category_stats.keys())
        
        col1, col2 = st.columns(2)
        
        with col1:
            category_to_delete = st.selectbox(
                "Select category to delete",
                categories,
                key="delete_category"
            )
            
            if category_to_delete:
                stats = category_stats[category_to_delete]
                st.warning(f"This will affect {stats['transaction_count']} transactions")
        
        with col2:
            replacement_options = ["Uncategorized"] + [cat for cat in categories if cat != category_to_delete]
            replacement_category = st.selectbox(
                "Replacement category",
                replacement_options,
                key="delete_replacement"
            )
        
        if category_to_delete and replacement_category:
            st.write(f"**Action:** Move all transactions from '{category_to_delete}' to '{replacement_category}'")
            
            if st.button("Delete Category", type="secondary", key="delete_button"):
                try:
                    updated_count = self.db.delete_category(category_to_delete, replacement_category)
                    st.success(f"Successfully deleted category '{category_to_delete}' and moved {updated_count} transactions to '{replacement_category}'")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete category: {e}")
    
    def _show_auto_categorize_tab(self):
        """Show the auto-categorization interface."""
        st.write("**Auto-categorize transactions based on description patterns**")
        st.info("This feature suggests categories based on common patterns in transaction descriptions.")
        
        # Get uncategorized or poorly categorized transactions
        uncategorized = [t for t in st.session_state.transactions 
                        if t.category.lower() in ['uncategorized', 'other', 'misc', 'miscellaneous']]
        
        if not uncategorized:
            st.success("All transactions appear to be categorized!")
            return
        
        st.write(f"Found {len(uncategorized)} transactions that could benefit from auto-categorization")
        
        # Common categorization patterns
        patterns = {
            'Groceries': ['grocery', 'supermarket', 'food', 'market', 'kroger', 'walmart', 'target'],
            'Gas': ['gas', 'fuel', 'shell', 'exxon', 'bp', 'chevron', 'mobil'],
            'Restaurants': ['restaurant', 'cafe', 'coffee', 'starbucks', 'mcdonald', 'subway', 'pizza'],
            'Shopping': ['amazon', 'ebay', 'store', 'shop', 'retail', 'mall'],
            'Utilities': ['electric', 'water', 'gas bill', 'internet', 'phone', 'cable'],
            'Transportation': ['uber', 'lyft', 'taxi', 'bus', 'train', 'parking'],
            'Entertainment': ['movie', 'theater', 'netflix', 'spotify', 'game', 'entertainment'],
            'Healthcare': ['medical', 'doctor', 'pharmacy', 'hospital', 'health', 'dental']
        }
        
        suggestions = {}
        for transaction in uncategorized:
            desc_lower = transaction.description.lower()
            for category, keywords in patterns.items():
                if any(keyword in desc_lower for keyword in keywords):
                    if category not in suggestions:
                        suggestions[category] = []
                    suggestions[category].append(transaction)
                    break
        
        if suggestions:
            st.write("**Categorization Suggestions:**")
            
            for category, transactions in suggestions.items():
                with st.expander(f"{category} ({len(transactions)} transactions)"):
                    # Show sample transactions
                    sample_transactions = transactions[:5]
                    for t in sample_transactions:
                        st.write(f"• {t.transaction_date.strftime('%Y-%m-%d')} - {t.description} - ${t.amount:.2f}")
                    
                    if len(transactions) > 5:
                        st.write(f"... and {len(transactions) - 5} more")
                    
                    if st.button(f"Apply '{category}' to {len(transactions)} transactions", key=f"auto_cat_{category}"):
                        try:
                            updated_count = 0
                            for transaction in transactions:
                                if self.db.update_transaction_category(transaction.id, category):
                                    updated_count += 1
                            
                            st.success(f"Successfully categorized {updated_count} transactions as '{category}'")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to auto-categorize: {e}")
        else:
            st.info("No automatic categorization suggestions found for uncategorized transactions.")