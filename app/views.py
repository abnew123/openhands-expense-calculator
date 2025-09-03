import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Optional
import logging
import json

from app.db import DatabaseManager
from app.csv_parser import CSVParser
from app.models import Transaction
from app.export_import import DataExporter, DataImporter, create_download_link
from app.performance import perf_monitor, StreamlitCache, show_performance_metrics, optimize_large_dataset_display, show_pagination_controls, optimize_chart_data
from app.error_handling import error_handler, safe_operation, ProgressTracker, show_success_message, show_warning_message, validate_user_input


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
        pages = ["📊 Dashboard", "📁 Upload CSV", "📋 Transactions", "📈 Analytics", "🏷️ Categories", "💾 Data Management"]
        
        # Add performance page for large datasets or debugging
        if st.session_state.get('large_dataset', False) or st.sidebar.checkbox("Show Performance", key="show_perf"):
            pages.append("⚡ Performance")
        
        page = st.sidebar.selectbox("Navigation", pages)
        
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
        elif page == "💾 Data Management":
            self._show_data_management_page()
        elif page == "⚡ Performance":
            self._show_performance_page()
    
    @perf_monitor.time_operation("load_data")
    def _load_data(self):
        """Load transactions and categories from database with performance optimization."""
        try:
            # Use cached data when possible
            transaction_count = StreamlitCache.get_cached_transaction_count(self.db.db_path)
            
            if transaction_count > 1000:
                # For large datasets, load with pagination
                st.session_state.transactions = self.db.get_transactions_paginated(page=1, page_size=1000)
                st.session_state.large_dataset = True
            else:
                st.session_state.transactions = self.db.get_all_transactions()
                st.session_state.large_dataset = False
            
            # Use cached categories
            st.session_state.categories = StreamlitCache.get_cached_categories(self.db.db_path)
            st.session_state.filtered_transactions = st.session_state.transactions
            
            # Store performance info
            st.session_state.total_transaction_count = transaction_count
            
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
        st.header("📁 Upload CSV File")
        
        # Show supported formats
        st.markdown("Upload your bank transaction CSV file. The following formats are supported:")
        
        supported_formats = self.csv_parser.get_supported_formats()
        for format_name, format_info in supported_formats.items():
            with st.expander(f"📋 {format_info['name']} Format"):
                st.write("**Required columns:**")
                for col in format_info['required_columns']:
                    st.write(f"• {col}")
        
        # Format selection
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # File upload
            uploaded_file = st.file_uploader(
                "Choose a CSV file",
                type=['csv'],
                help="Upload a bank transaction CSV file"
            )
        
        with col2:
            # Format selection (optional)
            format_options = ["Auto-detect"] + [info['name'] for info in supported_formats.values()]
            selected_format = st.selectbox(
                "CSV Format",
                format_options,
                help="Select format or use auto-detection"
            )
        
        if uploaded_file is not None:
            try:
                # Read file content
                csv_content = uploaded_file.read().decode('utf-8')
                
                # Determine format
                if selected_format == "Auto-detect":
                    validation_result = self.csv_parser.validate_csv_format(csv_content, "auto")
                    
                    if not validation_result['valid']:
                        st.error("❌ Could not detect or validate CSV format")
                        st.error(f"**Error:** {validation_result['error_message']}")
                        
                        # Show detailed column information
                        if validation_result['actual_columns']:
                            st.info(f"**Found columns:** {', '.join(validation_result['actual_columns'])}")
                        
                        st.info("**Supported formats:**")
                        for format_key, format_info in supported_formats.items():
                            with st.expander(f"📋 {format_info['name']} Format"):
                                st.write("**Required columns:**")
                                for col in format_info['required_columns']:
                                    st.write(f"• {col}")
                        return
                    
                    format_to_use = validation_result['detected_format']
                    format_name = supported_formats[format_to_use]['name']
                    st.success(f"✅ Detected format: {format_name}")
                    
                    # Show any extra columns as info
                    if validation_result['extra_columns']:
                        st.info(f"**Note:** Found additional columns that will be ignored: {', '.join(validation_result['extra_columns'])}")
                        
                else:
                    # Find format by name
                    format_to_use = None
                    for format_key, format_info in supported_formats.items():
                        if format_info['name'] == selected_format:
                            format_to_use = format_key
                            break
                    
                    if not format_to_use:
                        st.error("Invalid format selection")
                        return
                    
                    format_name = selected_format
                    
                    # Validate the specific format
                    validation_result = self.csv_parser.validate_csv_format(csv_content, format_to_use)
                    
                    if not validation_result['valid']:
                        st.error(f"❌ Invalid CSV format for {format_name}")
                        st.error(f"**Error:** {validation_result['error_message']}")
                        
                        # Show detailed column information
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Expected columns:**")
                            for col in validation_result['expected_columns']:
                                st.write(f"• {col}")
                        
                        with col2:
                            st.write("**Found columns:**")
                            for col in validation_result['actual_columns']:
                                st.write(f"• {col}")
                        
                        if validation_result['missing_columns']:
                            st.error(f"**Missing columns:** {', '.join(validation_result['missing_columns'])}")
                        
                        if validation_result['extra_columns']:
                            st.warning(f"**Extra columns:** {', '.join(validation_result['extra_columns'])}")
                        
                        return
                    return
                
                # Show preview
                st.subheader("📋 Preview")
                preview_df = self.csv_parser.get_csv_preview(csv_content)
                st.dataframe(preview_df, use_container_width=True)
                
                # Parse transactions
                transactions = self.csv_parser.parse_csv_generic(csv_content, format_to_use)
                
                if not transactions:
                    st.warning("No valid transactions found in the CSV file.")
                    return
                
                st.success(f"Found {len(transactions)} transactions")
                
                # Enhanced duplicate detection with options
                duplicate_analysis = self._analyze_duplicates(transactions)
                
                # Show duplicate analysis results
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Transactions", len(transactions))
                with col2:
                    st.metric("New Transactions", duplicate_analysis['new_count'])
                with col3:
                    st.metric("Potential Duplicates", duplicate_analysis['duplicate_count'])
                
                # Show duplicate detection options
                if duplicate_analysis['duplicate_count'] > 0:
                    st.subheader("🔍 Duplicate Detection Results")
                    
                    duplicate_handling = st.radio(
                        "How would you like to handle duplicates?",
                        [
                            "Skip all duplicates (recommended)",
                            "Import all transactions (may create duplicates)",
                            "Review duplicates manually"
                        ],
                        key="duplicate_handling"
                    )
                    
                    if duplicate_handling == "Review duplicates manually":
                        self._show_duplicate_review(duplicate_analysis['duplicates'])
                        return
                    elif duplicate_handling == "Import all transactions (may create duplicates)":
                        new_transactions = transactions
                        st.warning("⚠️ This will import all transactions, potentially creating duplicates.")
                    else:
                        new_transactions = duplicate_analysis['new_transactions']
                        st.info(f"Will skip {duplicate_analysis['duplicate_count']} duplicate transactions.")
                else:
                    new_transactions = transactions
                
                if new_transactions:
                    st.info(f"Ready to import {len(new_transactions)} transactions.")
                    
                    if st.button("Import Transactions", type="primary"):
                        self._import_transactions_with_progress(new_transactions)
                else:
                    st.info("No new transactions to import after duplicate filtering.")
                    
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
        """Display the enhanced analytics and charts page."""
        st.header("📈 Analytics & Insights")
        
        if not st.session_state.filtered_transactions:
            st.info("No transactions to analyze. Upload data or adjust filters.")
            return
        
        # Show filters
        self._show_filters()
        
        transactions = st.session_state.filtered_transactions
        expenses = [t for t in transactions if t.is_expense()]
        payments = [t for t in transactions if t.is_payment()]
        
        if not transactions:
            st.warning("No transactions match the current filters.")
            return
        
        # Analytics summary
        self._show_analytics_summary(transactions, expenses, payments)
        
        # Chart export controls
        st.subheader("📊 Visualizations")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write("Interactive charts with hover details and click-to-filter functionality")
        with col2:
            chart_format = st.selectbox("Export Format", ["PNG", "HTML", "SVG"], key="chart_export_format")
        with col3:
            if st.button("📥 Export All Charts", key="export_charts"):
                self._export_charts(expenses, chart_format)
        
        # Enhanced visualizations
        if expenses:
            # Category analysis
            st.subheader("💰 Spending by Category")
            self._show_enhanced_category_charts(expenses)
            
            # Sankey diagram
            st.subheader("🌊 Money Flow Analysis (Sankey Diagram)")
            self._show_sankey_diagram(transactions)
            
            # Time-based analysis
            st.subheader("📅 Spending Trends")
            self._show_enhanced_timeline_charts(expenses)
            
            # Transaction analysis
            st.subheader("🔍 Transaction Analysis")
            self._show_transaction_analysis_charts(expenses)
        
        if payments:
            st.subheader("💳 Payment Analysis")
            self._show_payment_analysis(payments)
    
    def _show_filters(self):
        """Display enhanced filter controls with date presets."""
        with st.expander("🔍 Filters", expanded=True):
            # Check if we have transactions
            if not st.session_state.transactions:
                st.info("No transactions available for filtering.")
                return
            
            # Get date bounds from transactions
            try:
                min_date = min(t.transaction_date for t in st.session_state.transactions).date()
                max_date = max(t.transaction_date for t in st.session_state.transactions).date()
            except (ValueError, AttributeError) as e:
                st.error("Error getting date range from transactions. Please reload the data.")
                self.logger.error(f"Date range error: {e}")
                return
            
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
                    # Use session state to maintain custom range, but validate it
                    if 'custom_date_range' not in st.session_state:
                        st.session_state.custom_date_range = (min_date, max_date)
                    else:
                        # Validate existing custom range against current data bounds
                        current_start, current_end = st.session_state.custom_date_range
                        
                        # If the stored range is outside current data bounds, reset it
                        if (current_start < min_date or current_start > max_date or 
                            current_end < min_date or current_end > max_date):
                            st.session_state.custom_date_range = (min_date, max_date)
                            st.info("Date range was reset because it was outside the current data range.")
                    
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
    
    @perf_monitor.time_operation("show_transactions_table")
    def _show_transactions_table(self):
        """Display transactions in an enhanced table with search and sorting."""
        transactions = st.session_state.filtered_transactions
        
        # Show performance warning for large datasets
        if len(transactions) > 500:
            st.info(f"⚡ Large dataset detected ({len(transactions)} transactions). Using optimized display.")
        
        # Transaction management controls
        st.subheader("🛠️ Transaction Management")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🗑️ Delete Selected", key="delete_selected", help="Delete selected transactions"):
                if 'selected_transactions' in st.session_state and st.session_state.selected_transactions:
                    self._delete_selected_transactions()
                else:
                    st.warning("No transactions selected")
        
        with col2:
            if st.button("📝 Edit Selected", key="edit_selected", help="Edit selected transactions"):
                if 'selected_transactions' in st.session_state and st.session_state.selected_transactions:
                    st.session_state.show_edit_modal = True
                else:
                    st.warning("No transactions selected")
        
        with col3:
            if st.button("🔄 Reset All Data", key="reset_all", help="Delete ALL transactions"):
                st.session_state.show_reset_confirmation = True
        
        with col4:
            if st.button("🔍 Advanced Search", key="advanced_search", help="Advanced search and filtering"):
                st.session_state.show_advanced_search = True
        
        # Show modals
        self._show_transaction_modals()
        
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
                        if self._update_category_safe(selected_transaction.id, new_category):
                            st.rerun()
    
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
                        if self._bulk_update_categories_with_progress(matching_transactions, new_bulk_category):
                            st.rerun()
    
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
        
        # Category hierarchy management
        st.subheader("🏗️ Category Hierarchy")
        
        tab1, tab2 = st.tabs(["View Hierarchy", "Manage Hierarchy"])
        
        with tab1:
            self._show_category_hierarchy_view()
        
        with tab2:
            self._show_category_hierarchy_management()
        
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
    
    def _show_analytics_summary(self, transactions, expenses, payments):
        """Show analytics summary metrics."""
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_expenses = sum(abs(t.amount) for t in expenses)
        total_payments = sum(t.amount for t in payments)
        avg_expense = total_expenses / len(expenses) if expenses else 0
        largest_expense = max(abs(t.amount) for t in expenses) if expenses else 0
        
        with col1:
            st.metric("Total Expenses", f"${total_expenses:.2f}")
        with col2:
            st.metric("Total Payments", f"${total_payments:.2f}")
        with col3:
            st.metric("Net Amount", f"${total_payments - total_expenses:.2f}")
        with col4:
            st.metric("Avg Expense", f"${avg_expense:.2f}")
        with col5:
            st.metric("Largest Expense", f"${largest_expense:.2f}")
    
    @perf_monitor.time_operation("show_enhanced_category_charts")
    def _show_enhanced_category_charts(self, expenses):
        """Show enhanced category visualization charts."""
        # Optimize for large datasets
        if len(expenses) > 1000:
            st.info(f"⚡ Optimizing charts for {len(expenses)} transactions")
        
        category_data = {}
        for t in expenses:
            category_data[t.category] = category_data.get(t.category, 0) + abs(t.amount)
        
        if not category_data:
            st.info("No expense data available for category analysis.")
            return
        
        # Sort categories by amount
        sorted_categories = sorted(category_data.items(), key=lambda x: x[1], reverse=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Enhanced pie chart with better formatting
            fig_pie = px.pie(
                values=[item[1] for item in sorted_categories],
                names=[item[0] for item in sorted_categories],
                title="Spending Distribution by Category",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Amount: $%{value:.2f}<br>Percentage: %{percent}<extra></extra>'
            )
            fig_pie.update_layout(showlegend=True, height=400)
            st.plotly_chart(fig_pie, use_container_width=True, key="category_pie")
        
        with col2:
            # Enhanced bar chart with better formatting
            fig_bar = px.bar(
                x=[item[0] for item in sorted_categories],
                y=[item[1] for item in sorted_categories],
                title="Spending by Category (Detailed)",
                labels={'x': 'Category', 'y': 'Amount ($)'},
                color=[item[1] for item in sorted_categories],
                color_continuous_scale='Viridis'
            )
            fig_bar.update_traces(
                hovertemplate='<b>%{x}</b><br>Amount: $%{y:.2f}<extra></extra>'
            )
            fig_bar.update_layout(
                xaxis_tickangle=-45,
                height=400,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_bar, use_container_width=True, key="category_bar")
        
        # Category comparison table
        st.write("**Category Breakdown**")
        total_expenses = sum(item[1] for item in sorted_categories)
        
        comparison_data = []
        for category, amount in sorted_categories:
            percentage = (amount / total_expenses) * 100
            transaction_count = len([t for t in expenses if t.category == category])
            avg_per_transaction = amount / transaction_count if transaction_count > 0 else 0
            
            comparison_data.append({
                'Category': category,
                'Amount': f"${amount:.2f}",
                'Percentage': f"{percentage:.1f}%",
                'Transactions': transaction_count,
                'Avg per Transaction': f"${avg_per_transaction:.2f}"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    def _show_enhanced_timeline_charts(self, expenses):
        """Show enhanced timeline visualization charts."""
        if not expenses:
            st.info("No expense data available for timeline analysis.")
            return
        
        # Monthly spending analysis
        monthly_data = {}
        daily_data = {}
        
        for t in expenses:
            month_key = t.transaction_date.strftime('%Y-%m')
            day_key = t.transaction_date.strftime('%Y-%m-%d')
            amount = abs(t.amount)
            
            monthly_data[month_key] = monthly_data.get(month_key, 0) + amount
            daily_data[day_key] = daily_data.get(day_key, 0) + amount
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Monthly trend
            if len(monthly_data) > 1:
                months = sorted(monthly_data.keys())
                amounts = [monthly_data[month] for month in months]
                
                fig_monthly = px.line(
                    x=months,
                    y=amounts,
                    title="Monthly Spending Trend",
                    labels={'x': 'Month', 'y': 'Amount ($)'},
                    markers=True
                )
                fig_monthly.update_traces(
                    line=dict(width=3),
                    marker=dict(size=8),
                    hovertemplate='<b>%{x}</b><br>Amount: $%{y:.2f}<extra></extra>'
                )
                fig_monthly.update_layout(height=400)
                st.plotly_chart(fig_monthly, use_container_width=True, key="monthly_trend")
            else:
                st.info("Need multiple months of data for trend analysis.")
        
        with col2:
            # Daily spending pattern (last 30 days if available)
            if len(daily_data) > 7:
                recent_days = sorted(daily_data.keys())[-30:]  # Last 30 days
                recent_amounts = [daily_data[day] for day in recent_days]
                
                fig_daily = px.bar(
                    x=recent_days,
                    y=recent_amounts,
                    title="Daily Spending Pattern (Last 30 Days)",
                    labels={'x': 'Date', 'y': 'Amount ($)'}
                )
                fig_daily.update_traces(
                    hovertemplate='<b>%{x}</b><br>Amount: $%{y:.2f}<extra></extra>'
                )
                fig_daily.update_layout(
                    xaxis_tickangle=-45,
                    height=400
                )
                st.plotly_chart(fig_daily, use_container_width=True, key="daily_pattern")
            else:
                st.info("Need more daily data for pattern analysis.")
        
        # Category trends over time
        if len(monthly_data) > 1:
            st.write("**Category Trends Over Time**")
            
            # Get top 5 categories
            category_totals = {}
            for t in expenses:
                category_totals[t.category] = category_totals.get(t.category, 0) + abs(t.amount)
            
            top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Build monthly data for each category
            category_monthly_data = {}
            for category, _ in top_categories:
                category_monthly_data[category] = {}
                for t in expenses:
                    if t.category == category:
                        month_key = t.transaction_date.strftime('%Y-%m')
                        category_monthly_data[category][month_key] = (
                            category_monthly_data[category].get(month_key, 0) + abs(t.amount)
                        )
            
            # Create multi-line chart
            fig_category_trends = go.Figure()
            
            months = sorted(monthly_data.keys())
            colors = px.colors.qualitative.Set1
            
            for i, (category, _) in enumerate(top_categories):
                amounts = [category_monthly_data[category].get(month, 0) for month in months]
                fig_category_trends.add_trace(go.Scatter(
                    x=months,
                    y=amounts,
                    mode='lines+markers',
                    name=category,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=6),
                    hovertemplate=f'<b>{category}</b><br>%{{x}}<br>Amount: $%{{y:.2f}}<extra></extra>'
                ))
            
            fig_category_trends.update_layout(
                title="Top Categories Spending Trends",
                xaxis_title="Month",
                yaxis_title="Amount ($)",
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_category_trends, use_container_width=True, key="category_trends")
    
    def _show_transaction_analysis_charts(self, expenses):
        """Show transaction analysis charts."""
        if not expenses:
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Amount distribution histogram
            amounts = [abs(t.amount) for t in expenses]
            
            fig_hist = px.histogram(
                x=amounts,
                nbins=20,
                title="Transaction Amount Distribution",
                labels={'x': 'Amount ($)', 'y': 'Number of Transactions'}
            )
            fig_hist.update_traces(
                hovertemplate='Amount Range: $%{x}<br>Transactions: %{y}<extra></extra>'
            )
            fig_hist.update_layout(height=400)
            st.plotly_chart(fig_hist, use_container_width=True, key="amount_distribution")
        
        with col2:
            # Day of week analysis
            day_spending = {}
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            for t in expenses:
                day_name = day_names[t.transaction_date.weekday()]
                day_spending[day_name] = day_spending.get(day_name, 0) + abs(t.amount)
            
            # Ensure all days are present
            for day in day_names:
                if day not in day_spending:
                    day_spending[day] = 0
            
            fig_dow = px.bar(
                x=day_names,
                y=[day_spending[day] for day in day_names],
                title="Spending by Day of Week",
                labels={'x': 'Day of Week', 'y': 'Amount ($)'},
                color=[day_spending[day] for day in day_names],
                color_continuous_scale='Blues'
            )
            fig_dow.update_traces(
                hovertemplate='<b>%{x}</b><br>Amount: $%{y:.2f}<extra></extra>'
            )
            fig_dow.update_layout(height=400, coloraxis_showscale=False)
            st.plotly_chart(fig_dow, use_container_width=True, key="day_of_week")
    
    def _show_payment_analysis(self, payments):
        """Show payment analysis charts."""
        if not payments:
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Payment amounts over time
            payment_data = {}
            for t in payments:
                month_key = t.transaction_date.strftime('%Y-%m')
                payment_data[month_key] = payment_data.get(month_key, 0) + t.amount
            
            if payment_data:
                months = sorted(payment_data.keys())
                amounts = [payment_data[month] for month in months]
                
                fig_payments = px.bar(
                    x=months,
                    y=amounts,
                    title="Monthly Payments",
                    labels={'x': 'Month', 'y': 'Amount ($)'},
                    color=amounts,
                    color_continuous_scale='Greens'
                )
                fig_payments.update_traces(
                    hovertemplate='<b>%{x}</b><br>Amount: $%{y:.2f}<extra></extra>'
                )
                fig_payments.update_layout(height=400, coloraxis_showscale=False)
                st.plotly_chart(fig_payments, use_container_width=True, key="monthly_payments")
        
        with col2:
            # Payment summary
            total_payments = sum(t.amount for t in payments)
            avg_payment = total_payments / len(payments) if payments else 0
            largest_payment = max(t.amount for t in payments) if payments else 0
            
            st.metric("Total Payments", f"${total_payments:.2f}")
            st.metric("Average Payment", f"${avg_payment:.2f}")
            st.metric("Largest Payment", f"${largest_payment:.2f}")
            st.metric("Number of Payments", len(payments))
    
    def _export_charts(self, expenses, format_type):
        """Export charts in specified format."""
        try:
            import plotly.io as pio
            import base64
            from io import BytesIO
            
            st.info(f"Exporting charts in {format_type} format...")
            
            # This is a placeholder for chart export functionality
            # In a real implementation, you would generate and download the charts
            st.success(f"Chart export in {format_type} format would be implemented here.")
            st.info("Note: Full export functionality requires additional implementation for file downloads.")
            
        except Exception as e:
            st.error(f"Export failed: {e}")
    
    def _show_data_management_page(self):
        """Display the data management page for export/import operations."""
        st.header("💾 Data Management")
        st.markdown("Export your data for backup or import data from previous exports.")
        
        if not st.session_state.transactions:
            st.info("No transactions found. Upload data first to use export features.")
            return
        
        # Initialize exporters
        exporter = DataExporter(self.db)
        importer = DataImporter(self.db)
        
        tab1, tab2, tab3 = st.tabs(["📤 Export Data", "📥 Import Data", "📊 Backup & Restore"])
        
        with tab1:
            self._show_export_tab(exporter)
        
        with tab2:
            self._show_import_tab(importer)
        
        with tab3:
            self._show_backup_restore_tab(exporter, importer)
    
    def _show_export_tab(self, exporter: DataExporter):
        """Show the export data interface."""
        st.subheader("📤 Export Your Data")
        
        # Export options
        col1, col2 = st.columns(2)
        
        with col1:
            export_scope = st.radio(
                "Export Scope",
                ["All Transactions", "Filtered Transactions", "Category Statistics Only"],
                key="export_scope"
            )
        
        with col2:
            export_format = st.radio(
                "Export Format",
                ["CSV", "JSON"],
                key="export_format"
            )
        
        # Show what will be exported
        if export_scope == "All Transactions":
            transactions_to_export = st.session_state.transactions
            st.info(f"Will export {len(transactions_to_export)} total transactions")
        elif export_scope == "Filtered Transactions":
            transactions_to_export = st.session_state.filtered_transactions
            st.info(f"Will export {len(transactions_to_export)} filtered transactions")
        else:
            transactions_to_export = []
            st.info("Will export category statistics only")
        
        # Export buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Generate Export", type="primary", key="generate_export"):
                try:
                    if export_scope == "Category Statistics Only":
                        if export_format == "CSV":
                            content = exporter.export_category_stats_to_csv()
                            filename = f"category_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                            content_type = "text/csv"
                        else:
                            # JSON export of just category stats
                            stats_data = {
                                'metadata': {
                                    'export_date': datetime.now().isoformat(),
                                    'version': '1.0',
                                    'export_type': 'category_statistics',
                                    'application': 'Personal Expense Tracker'
                                },
                                'category_stats': self.db.get_category_stats(),
                                'categories': self.db.get_categories()
                            }
                            content = json.dumps(stats_data, indent=2, ensure_ascii=False)
                            filename = f"category_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            content_type = "application/json"
                    else:
                        if export_format == "CSV":
                            content = exporter.export_to_csv(transactions_to_export)
                            filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                            content_type = "text/csv"
                        else:
                            content = exporter.export_to_json(transactions_to_export)
                            filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            content_type = "application/json"
                    
                    # Store in session state for download
                    st.session_state.export_content = content
                    st.session_state.export_filename = filename
                    st.session_state.export_content_type = content_type
                    
                    st.success(f"Export generated successfully! File size: {len(content)} characters")
                    
                except Exception as e:
                    st.error(f"Export failed: {e}")
        
        with col2:
            if 'export_content' in st.session_state:
                # Create download button
                st.download_button(
                    label=f"📥 Download {st.session_state.export_filename}",
                    data=st.session_state.export_content,
                    file_name=st.session_state.export_filename,
                    mime=st.session_state.export_content_type,
                    key="download_export"
                )
        
        with col3:
            if 'export_content' in st.session_state:
                if st.button("🗑️ Clear Export", key="clear_export"):
                    del st.session_state.export_content
                    del st.session_state.export_filename
                    del st.session_state.export_content_type
                    st.rerun()
        
        # Preview export content
        if 'export_content' in st.session_state:
            st.subheader("📋 Export Preview")
            
            # Show first few lines of export
            content_lines = st.session_state.export_content.split('\n')
            preview_lines = content_lines[:10]
            
            st.code('\n'.join(preview_lines), language='text')
            
            if len(content_lines) > 10:
                st.write(f"... and {len(content_lines) - 10} more lines")
    
    def _show_import_tab(self, importer: DataImporter):
        """Show the import data interface."""
        st.subheader("📥 Import Data")
        st.markdown("Import transaction data from previous exports (JSON format only).")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a JSON export file",
            type=['json'],
            help="Upload a JSON file exported from this application",
            key="import_file"
        )
        
        if uploaded_file is not None:
            try:
                # Read file content
                json_content = uploaded_file.read().decode('utf-8')
                
                # Validate import data
                validation_result = importer.validate_json_import(json_content)
                
                st.subheader("📋 Import Validation")
                
                if validation_result['valid']:
                    st.success("✅ Import file is valid!")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Total Transactions", validation_result['total_transactions'])
                        st.metric("Valid Transactions", validation_result['valid_transactions'])
                    
                    with col2:
                        st.metric("Categories Found", len(validation_result['categories_found']))
                        if validation_result.get('has_category_stats'):
                            st.info("✅ Includes category statistics")
                    
                    # Show metadata if available
                    if validation_result.get('metadata'):
                        st.write("**Export Metadata:**")
                        metadata = validation_result['metadata']
                        for key, value in metadata.items():
                            st.write(f"- **{key.replace('_', ' ').title()}**: {value}")
                    
                    # Show categories
                    if validation_result['categories_found']:
                        st.write("**Categories in import:**")
                        st.write(", ".join(validation_result['categories_found']))
                    
                    # Import button
                    if st.button("📥 Import Transactions", type="primary", key="import_transactions"):
                        try:
                            with st.spinner("Importing transactions..."):
                                import_result = importer.import_from_json(json_content)
                            
                            st.success("Import completed!")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Imported", import_result['imported'])
                            with col2:
                                st.metric("Duplicates Skipped", import_result['duplicates'])
                            with col3:
                                st.metric("Errors", import_result['errors'])
                            
                            if import_result['imported'] > 0:
                                st.info("Please refresh the page to see imported transactions.")
                                if st.button("🔄 Refresh Page", key="refresh_after_import"):
                                    st.rerun()
                            
                        except Exception as e:
                            st.error(f"Import failed: {e}")
                
                else:
                    st.error("❌ Import file validation failed!")
                    if 'error' in validation_result:
                        st.error(validation_result['error'])
                    if 'warning' in validation_result:
                        st.warning(validation_result['warning'])
                    
                    if validation_result['invalid_transactions'] > 0:
                        st.write(f"Found {validation_result['invalid_transactions']} invalid transactions")
                
            except Exception as e:
                st.error(f"Failed to process import file: {e}")
    
    def _show_backup_restore_tab(self, exporter: DataExporter, importer: DataImporter):
        """Show backup and restore interface."""
        st.subheader("📊 Backup & Restore")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🔄 Create Full Backup**")
            st.write("Create a complete backup of all your data including transactions, categories, and statistics.")
            
            backup_type = st.radio(
                "Backup Type",
                ["JSON Export", "Database File"],
                key="backup_type"
            )
            
            if st.button("📦 Create Full Backup", type="primary", key="create_backup"):
                try:
                    if backup_type == "JSON Export":
                        # Create comprehensive backup
                        backup_data = exporter.export_to_json(pretty=True)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"expense_tracker_backup_{timestamp}.json"
                        
                        st.session_state.backup_content = backup_data
                        st.session_state.backup_filename = filename
                        
                        st.success("JSON backup created successfully!")
                    else:
                        # Create database file backup
                        self._create_database_backup(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                    
                except Exception as e:
                    st.error(f"Backup creation failed: {e}")
            
            if 'backup_content' in st.session_state:
                st.download_button(
                    label=f"📥 Download {st.session_state.backup_filename}",
                    data=st.session_state.backup_content,
                    file_name=st.session_state.backup_filename,
                    mime="application/json",
                    key="download_backup"
                )
        
        with col2:
            st.write("**📂 Restore from Backup**")
            st.write("Restore data from a previous backup file.")
            
            restore_type = st.radio(
                "Restore Type",
                ["JSON Backup", "Database File"],
                key="restore_type"
            )
            
            if restore_type == "JSON Backup":
                backup_file = st.file_uploader(
                    "Choose JSON backup file",
                    type=['json'],
                    help="Upload a backup JSON file",
                    key="restore_json_file"
                )
            else:
                backup_file = st.file_uploader(
                    "Choose database backup file",
                    type=['db', 'sqlite', 'sqlite3'],
                    help="Upload a database backup file",
                    key="restore_db_file"
                )
            
            if backup_file is not None:
                if restore_type == "JSON Backup":
                    try:
                        backup_content = backup_file.read().decode('utf-8')
                        validation = importer.validate_json_import(backup_content)
                        
                        if validation['valid']:
                            st.success(f"✅ Valid backup with {validation['total_transactions']} transactions")
                            
                            st.warning("⚠️ This will add transactions to your existing data. Duplicates will be skipped.")
                            
                            if st.button("🔄 Restore from JSON Backup", key="restore_json_backup"):
                                try:
                                    result = importer.import_from_json(backup_content)
                                    st.success(f"Restored {result['imported']} transactions!")
                                    
                                    if st.button("🔄 Refresh Page", key="refresh_after_json_restore"):
                                        st.rerun()
                                        
                                except Exception as e:
                                    st.error(f"JSON restore failed: {e}")
                        else:
                            st.error("❌ Invalid JSON backup file")
                    except Exception as e:
                        st.error(f"Failed to process JSON backup: {e}")
                else:
                    # Database file restore
                    st.warning("⚠️ This will REPLACE ALL current data!")
                    
                    if st.button("🔄 Restore Database", key="restore_db_backup", type="primary"):
                        self._restore_database_backup(backup_file)
        
        # Database statistics
        st.subheader("📈 Database Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Transactions", len(st.session_state.transactions))
        
        with col2:
            st.metric("Categories", len(st.session_state.categories))
        
        with col3:
            expenses = [t for t in st.session_state.transactions if t.is_expense()]
            st.metric("Expenses", len(expenses))
        
        with col4:
            payments = [t for t in st.session_state.transactions if t.is_payment()]
            st.metric("Payments", len(payments))
    
    def _show_performance_page(self):
        """Display performance monitoring and optimization page."""
        st.header("⚡ Performance Monitoring")
        st.markdown("Monitor application performance and optimize for large datasets.")
        
        # Dataset information
        st.subheader("📊 Dataset Information")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_count = st.session_state.get('total_transaction_count', len(st.session_state.transactions))
            st.metric("Total Transactions", total_count)
        
        with col2:
            loaded_count = len(st.session_state.transactions)
            st.metric("Loaded in Memory", loaded_count)
        
        with col3:
            filtered_count = len(st.session_state.filtered_transactions)
            st.metric("Currently Filtered", filtered_count)
        
        with col4:
            is_large = st.session_state.get('large_dataset', False)
            st.metric("Large Dataset Mode", "Yes" if is_large else "No")
        
        # Performance recommendations
        st.subheader("💡 Performance Recommendations")
        
        total_count = st.session_state.get('total_transaction_count', 0)
        
        if total_count > 5000:
            st.error("⚠️ Very large dataset detected (5000+ transactions)")
            st.write("**Recommendations:**")
            st.write("- Use date filters to reduce data load")
            st.write("- Consider archiving old transactions")
            st.write("- Use export/import for data management")
        elif total_count > 1000:
            st.warning("⚠️ Large dataset detected (1000+ transactions)")
            st.write("**Recommendations:**")
            st.write("- Charts and tables are optimized automatically")
            st.write("- Use filters to focus on specific time periods")
        else:
            st.success("✅ Dataset size is optimal for performance")
        
        # Performance metrics
        show_performance_metrics()
        
        # Cache management
        st.subheader("🗄️ Cache Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear Cache", key="clear_cache"):
                StreamlitCache.clear_all_cache()
                st.success("Cache cleared successfully!")
                st.info("Refresh the page to reload data.")
        
        with col2:
            if st.button("🔄 Reload Data", key="reload_data"):
                StreamlitCache.clear_all_cache()
                st.rerun()
        
        # Database optimization
        st.subheader("🔧 Database Optimization")
        
        if st.button("📊 Analyze Database", key="analyze_db"):
            try:
                with st.spinner("Analyzing database performance..."):
                    # Run ANALYZE command to update statistics
                    import sqlite3
                    with sqlite3.connect(self.db.db_path) as conn:
                        conn.execute("ANALYZE")
                        
                        # Get database size
                        cursor = conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                        db_size = cursor.fetchone()[0]
                        
                        # Get index information
                        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
                        indexes = [row[0] for row in cursor.fetchall()]
                
                st.success("Database analysis completed!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Database Size", f"{db_size / 1024 / 1024:.2f} MB")
                with col2:
                    st.metric("Indexes", len(indexes))
                
                if indexes:
                    st.write("**Active Indexes:**")
                    for idx in indexes:
                        st.write(f"- {idx}")
                
            except Exception as e:
                st.error(f"Database analysis failed: {e}")
        
        # Memory usage (approximate)
        st.subheader("💾 Memory Usage")
        
        import sys
        
        transactions_size = sys.getsizeof(st.session_state.transactions) / 1024 / 1024
        filtered_size = sys.getsizeof(st.session_state.filtered_transactions) / 1024 / 1024
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Transactions Memory", f"{transactions_size:.2f} MB")
        with col2:
            st.metric("Filtered Memory", f"{filtered_size:.2f} MB")
        
        if transactions_size > 50:
            st.warning("⚠️ High memory usage detected. Consider using filters or pagination.")
    
    @safe_operation("transaction import", show_spinner=False)
    def _import_transactions_with_progress(self, transactions):
        """Import transactions with progress tracking and error handling."""
        if not transactions:
            show_warning_message("No transactions to import")
            return
        
        # Create progress tracker
        progress = ProgressTracker(len(transactions) + 2, "Importing Transactions")
        
        try:
            # Step 1: Validate transactions
            progress.update(1, "Validating transaction data...")
            
            valid_transactions = []
            invalid_count = 0
            
            for i, transaction in enumerate(transactions):
                try:
                    # Basic validation
                    if not transaction.description.strip():
                        invalid_count += 1
                        continue
                    if transaction.amount == 0:
                        invalid_count += 1
                        continue
                    
                    valid_transactions.append(transaction)
                    
                    # Update progress every 100 transactions
                    if i % 100 == 0:
                        progress.update(1, f"Validated {i + 1} of {len(transactions)} transactions...")
                
                except Exception as e:
                    self.logger.warning(f"Invalid transaction skipped: {e}")
                    invalid_count += 1
            
            if invalid_count > 0:
                show_warning_message(f"Skipped {invalid_count} invalid transactions")
            
            if not valid_transactions:
                progress.error("No valid transactions found")
                return
            
            # Step 2: Insert transactions
            progress.update(len(transactions) + 1, f"Inserting {len(valid_transactions)} transactions...")
            
            transaction_ids = self.db.insert_transactions_batch(valid_transactions)
            
            # Step 3: Complete
            progress.complete(f"Successfully imported {len(transaction_ids)} transactions!")
            
            # Show summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Imported", len(transaction_ids))
            with col2:
                st.metric("Skipped (Invalid)", invalid_count)
            with col3:
                st.metric("Total Processed", len(transactions))
            
            # Offer to refresh
            if st.button("🔄 Refresh to See New Data", key="refresh_after_import"):
                st.rerun()
        
        except Exception as e:
            progress.error(str(e))
            error_handler.handle_database_error(e, "transaction import")
    
    @safe_operation("category update")
    def _update_category_safe(self, transaction_id: int, new_category: str):
        """Safely update transaction category with error handling."""
        if not validate_user_input(new_category, "required_text", "Category"):
            return False
        
        success = self.db.update_transaction_category(transaction_id, new_category)
        
        if success:
            show_success_message(f"Category updated to '{new_category}'")
            return True
        else:
            st.error("❌ Failed to update category")
            st.info("**Solution:** Please try again or check if the transaction still exists.")
            return False
    
    @safe_operation("bulk category update", show_spinner=False)
    def _bulk_update_categories_with_progress(self, transactions, new_category: str):
        """Bulk update categories with progress tracking."""
        if not transactions:
            show_warning_message("No transactions selected for update")
            return
        
        if not validate_user_input(new_category, "required_text", "New Category"):
            return
        
        # Create progress tracker
        progress = ProgressTracker(len(transactions), "Bulk Category Update")
        
        try:
            updated_count = 0
            failed_count = 0
            
            for i, transaction in enumerate(transactions):
                try:
                    if self.db.update_transaction_category(transaction.id, new_category):
                        updated_count += 1
                    else:
                        failed_count += 1
                    
                    # Update progress every 10 transactions
                    if i % 10 == 0 or i == len(transactions) - 1:
                        progress.update(i + 1, f"Updated {updated_count} of {i + 1} transactions...")
                
                except Exception as e:
                    self.logger.warning(f"Failed to update transaction {transaction.id}: {e}")
                    failed_count += 1
            
            # Complete with summary
            if updated_count > 0:
                progress.complete(f"Updated {updated_count} transactions to '{new_category}'")
                
                if failed_count > 0:
                    show_warning_message(f"{failed_count} transactions could not be updated")
                
                # Show summary
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Successfully Updated", updated_count)
                with col2:
                    st.metric("Failed", failed_count)
                
                return True
            else:
                progress.error("No transactions were updated")
                return False
        
        except Exception as e:
            progress.error(str(e))
            error_handler.handle_database_error(e, "bulk category update")
    
    def _show_transaction_modals(self):
        """Show transaction management modals."""
        # Reset confirmation modal
        if st.session_state.get('show_reset_confirmation', False):
            with st.container():
                st.error("⚠️ **DANGER ZONE** ⚠️")
                st.write("This will permanently delete ALL transactions. This action cannot be undone.")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if st.button("❌ Cancel", key="cancel_reset"):
                        st.session_state.show_reset_confirmation = False
                        st.experimental_rerun()
                
                with col2:
                    confirm_text = st.text_input("Type 'DELETE ALL' to confirm:", key="reset_confirm_text")
                
                with col3:
                    if st.button("🗑️ DELETE ALL", key="confirm_reset", type="primary"):
                        if confirm_text == "DELETE ALL":
                            deleted_count = self.db.delete_all_transactions()
                            st.success(f"✅ Deleted {deleted_count} transactions")
                            st.session_state.show_reset_confirmation = False
                            
                            # Clear date range filters and other session state
                            self._reset_filters_after_data_deletion()
                            
                            self._load_data()
                            st.experimental_rerun()
                        else:
                            st.error("Please type 'DELETE ALL' to confirm")
        
        # Edit modal
        if st.session_state.get('show_edit_modal', False):
            self._show_edit_transactions_modal()
        
        # Advanced search modal
        if st.session_state.get('show_advanced_search', False):
            self._show_advanced_search_modal()
    
    def _show_edit_transactions_modal(self):
        """Show modal for editing selected transactions."""
        with st.container():
            st.subheader("📝 Edit Selected Transactions")
            
            selected_ids = st.session_state.get('selected_transactions', [])
            st.write(f"Editing {len(selected_ids)} transactions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Category update
                new_category = st.selectbox(
                    "Update Category",
                    [""] + st.session_state.categories,
                    key="edit_category"
                )
                
                # Description pattern replacement
                find_text = st.text_input("Find in Description", key="edit_find")
                replace_text = st.text_input("Replace with", key="edit_replace")
            
            with col2:
                # Amount adjustment
                amount_adjustment = st.number_input(
                    "Amount Adjustment ($)",
                    value=0.0,
                    help="Add/subtract from current amount",
                    key="edit_amount_adj"
                )
                
                # Date adjustment
                date_adjustment = st.number_input(
                    "Date Adjustment (days)",
                    value=0,
                    help="Add/subtract days from current date",
                    key="edit_date_adj"
                )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("❌ Cancel", key="cancel_edit"):
                    st.session_state.show_edit_modal = False
                    st.experimental_rerun()
            
            with col2:
                if st.button("👁️ Preview Changes", key="preview_edit"):
                    self._preview_transaction_edits(selected_ids, new_category, find_text, replace_text, amount_adjustment, date_adjustment)
            
            with col3:
                if st.button("✅ Apply Changes", key="apply_edit", type="primary"):
                    self._apply_transaction_edits(selected_ids, new_category, find_text, replace_text, amount_adjustment, date_adjustment)
    
    def _show_advanced_search_modal(self):
        """Show advanced search and filtering modal."""
        with st.container():
            st.subheader("🔍 Advanced Search & Filter")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Text search with regex
                description_pattern = st.text_input(
                    "Description Pattern (supports regex)",
                    help="Use regex patterns like 'AMAZON.*' or simple text",
                    key="adv_description"
                )
                
                # Amount range
                amount_min = st.number_input("Minimum Amount ($)", value=None, key="adv_amount_min")
                amount_max = st.number_input("Maximum Amount ($)", value=None, key="adv_amount_max")
            
            with col2:
                # Date range
                if st.session_state.transactions:
                    min_date = min(t.transaction_date for t in st.session_state.transactions).date()
                    max_date = max(t.transaction_date for t in st.session_state.transactions).date()
                    
                    date_range = st.date_input(
                        "Date Range",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date,
                        key="adv_date_range"
                    )
                
                # Category selection
                selected_categories = st.multiselect(
                    "Categories",
                    st.session_state.categories,
                    key="adv_categories"
                )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("❌ Cancel", key="cancel_advanced_search"):
                    st.session_state.show_advanced_search = False
                    st.experimental_rerun()
            
            with col2:
                if st.button("🔍 Search", key="execute_advanced_search"):
                    self._execute_advanced_search(description_pattern, amount_min, amount_max, date_range, selected_categories)
            
            with col3:
                if st.button("🗑️ Delete Matching", key="delete_matching", type="primary"):
                    self._delete_matching_transactions(description_pattern, amount_min, amount_max, date_range, selected_categories)
    
    def _delete_selected_transactions(self):
        """Delete selected transactions."""
        selected_ids = st.session_state.get('selected_transactions', [])
        if selected_ids:
            deleted_count = self.db.delete_transactions_batch(selected_ids)
            st.success(f"✅ Deleted {deleted_count} transactions")
            st.session_state.selected_transactions = []
            self._load_data()
            st.experimental_rerun()
    
    def _apply_transaction_edits(self, transaction_ids, new_category, find_text, replace_text, amount_adjustment, date_adjustment):
        """Apply edits to selected transactions."""
        updates = {}
        updated_count = 0
        
        # Category update
        if new_category:
            updated_count += self.db.update_transactions_batch(transaction_ids, category=new_category)
        
        # Description replacement
        if find_text and replace_text:
            for tid in transaction_ids:
                # Get current transaction
                transactions = [t for t in st.session_state.transactions if t.id == tid]
                if transactions:
                    t = transactions[0]
                    new_description = t.description.replace(find_text, replace_text)
                    if new_description != t.description:
                        self.db.update_transaction(tid, description=new_description)
                        updated_count += 1
        
        # Amount adjustment
        if amount_adjustment != 0:
            for tid in transaction_ids:
                transactions = [t for t in st.session_state.transactions if t.id == tid]
                if transactions:
                    t = transactions[0]
                    new_amount = float(t.amount) + amount_adjustment
                    self.db.update_transaction(tid, amount=new_amount)
                    updated_count += 1
        
        # Date adjustment
        if date_adjustment != 0:
            for tid in transaction_ids:
                transactions = [t for t in st.session_state.transactions if t.id == tid]
                if transactions:
                    t = transactions[0]
                    new_date = t.transaction_date + timedelta(days=date_adjustment)
                    self.db.update_transaction(tid, transaction_date=new_date, post_date=new_date)
                    updated_count += 1
        
        st.success(f"✅ Updated {len(transaction_ids)} transactions")
        st.session_state.show_edit_modal = False
        self._load_data()
        st.experimental_rerun()
    
    def _preview_transaction_edits(self, transaction_ids, new_category, find_text, replace_text, amount_adjustment, date_adjustment):
        """Preview changes before applying."""
        st.write("**Preview of Changes:**")
        
        preview_data = []
        for tid in transaction_ids[:5]:  # Show first 5 as preview
            transactions = [t for t in st.session_state.transactions if t.id == tid]
            if transactions:
                t = transactions[0]
                
                # Calculate changes
                new_desc = t.description.replace(find_text, replace_text) if find_text and replace_text else t.description
                new_cat = new_category if new_category else t.category
                new_amt = float(t.amount) + amount_adjustment if amount_adjustment != 0 else float(t.amount)
                new_date = t.transaction_date + timedelta(days=date_adjustment) if date_adjustment != 0 else t.transaction_date
                
                preview_data.append({
                    'ID': tid,
                    'Old Description': t.description[:30] + "..." if len(t.description) > 30 else t.description,
                    'New Description': new_desc[:30] + "..." if len(new_desc) > 30 else new_desc,
                    'Old Category': t.category,
                    'New Category': new_cat,
                    'Old Amount': f"${t.amount:.2f}",
                    'New Amount': f"${new_amt:.2f}",
                    'Old Date': t.transaction_date.strftime('%Y-%m-%d'),
                    'New Date': new_date.strftime('%Y-%m-%d')
                })
        
        if preview_data:
            preview_df = pd.DataFrame(preview_data)
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
            
            if len(transaction_ids) > 5:
                st.info(f"Showing preview for first 5 transactions. {len(transaction_ids) - 5} more will be updated.")
    
    def _execute_advanced_search(self, description_pattern, amount_min, amount_max, date_range, selected_categories):
        """Execute advanced search and show results."""
        # This would filter the current view - implementation depends on how you want to handle it
        st.info("Advanced search executed - results would be shown in the main transaction table")
        st.session_state.show_advanced_search = False
        st.experimental_rerun()
    
    def _delete_matching_transactions(self, description_pattern, amount_min, amount_max, date_range, selected_categories):
        """Delete transactions matching advanced search criteria."""
        # Convert date_range to datetime objects
        start_date = None
        end_date = None
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date = datetime.combine(date_range[0], datetime.min.time())
            end_date = datetime.combine(date_range[1], datetime.max.time())
        
        # Use the database method to delete by criteria
        deleted_count = self.db.delete_transactions_by_criteria(
            description_pattern=description_pattern if description_pattern else None,
            amount_min=amount_min,
            amount_max=amount_max,
            start_date=start_date,
            end_date=end_date,
            category=selected_categories[0] if selected_categories and len(selected_categories) == 1 else None
        )
        
        st.success(f"✅ Deleted {deleted_count} matching transactions")
        st.session_state.show_advanced_search = False
        self._load_data()
        st.experimental_rerun()
    
    def _reset_filters_after_data_deletion(self):
        """Reset all filters and session state after data deletion."""
        # Clear date range filters
        if 'custom_date_range' in st.session_state:
            del st.session_state.custom_date_range
        
        # Clear other filter-related session state
        filter_keys_to_clear = [
            'date_preset',
            'category_filter', 
            'type_filter',
            'amount_filter',
            'transaction_search',
            'transaction_sort',
            'selected_transactions',
            'filtered_transactions'
        ]
        
        for key in filter_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Reset transactions and categories
        st.session_state.transactions = []
        st.session_state.categories = []
        st.session_state.filtered_transactions = []
        
        self.logger.info("Reset all filters and session state after data deletion")
    
    def _analyze_duplicates(self, transactions):
        """Analyze transactions for duplicates and return detailed results."""
        new_transactions = []
        duplicates = []
        
        for transaction in transactions:
            if not self.db.transaction_exists(transaction):
                new_transactions.append(transaction)
            else:
                # Find the specific duplicates for this transaction
                potential_duplicates = self.db.find_potential_duplicates(transaction)
                duplicates.append({
                    'new_transaction': transaction,
                    'existing_duplicates': potential_duplicates
                })
        
        return {
            'new_transactions': new_transactions,
            'new_count': len(new_transactions),
            'duplicates': duplicates,
            'duplicate_count': len(duplicates),
            'total_count': len(transactions)
        }
    
    def _show_duplicate_review(self, duplicates):
        """Show detailed duplicate review interface."""
        st.subheader("🔍 Review Potential Duplicates")
        st.write(f"Found {len(duplicates)} potential duplicates. Review each one below:")
        
        selected_to_import = []
        
        for i, duplicate_info in enumerate(duplicates):
            new_transaction = duplicate_info['new_transaction']
            existing_duplicates = duplicate_info['existing_duplicates']
            
            with st.expander(f"Duplicate {i+1}: {new_transaction.description[:50]}..."):
                st.write("**New Transaction (from CSV):**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"Date: {new_transaction.transaction_date.strftime('%Y-%m-%d')}")
                with col2:
                    st.write(f"Amount: ${new_transaction.amount:.2f}")
                with col3:
                    st.write(f"Description: {new_transaction.description}")
                
                st.write("**Existing Transactions in Database:**")
                for j, existing in enumerate(existing_duplicates):
                    st.write(f"**Match {j+1}:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"Date: {existing.transaction_date.strftime('%Y-%m-%d')}")
                    with col2:
                        st.write(f"Amount: ${existing.amount:.2f}")
                    with col3:
                        st.write(f"Description: {existing.description}")
                
                # Decision for this duplicate
                decision = st.radio(
                    f"Decision for transaction {i+1}:",
                    ["Skip (it's a duplicate)", "Import (it's different)"],
                    key=f"duplicate_decision_{i}"
                )
                
                if decision == "Import (it's different)":
                    selected_to_import.append(new_transaction)
        
        # Import selected transactions
        if selected_to_import:
            st.info(f"Selected {len(selected_to_import)} transactions to import.")
            
            if st.button("Import Selected Transactions", type="primary", key="import_selected"):
                self._import_transactions_with_progress(selected_to_import)
        else:
            st.info("No transactions selected for import.")
    
    def _show_sankey_diagram(self, transactions):
        """Show Sankey diagram for money flow analysis."""
        try:
            import plotly.graph_objects as go
            
            if not transactions:
                st.info("No transactions available for Sankey diagram.")
                return
            
            # Sankey diagram options
            col1, col2 = st.columns(2)
            
            with col1:
                sankey_type = st.selectbox(
                    "Sankey Diagram Type",
                    ["Income → Categories → Subcategories", "Monthly Flow", "Category Hierarchy"],
                    key="sankey_type"
                )
            
            with col2:
                time_period = st.selectbox(
                    "Time Period",
                    ["All Time", "Last 3 Months", "Last 6 Months", "This Year"],
                    key="sankey_period"
                )
            
            # Filter transactions by time period
            filtered_transactions = self._filter_transactions_by_period(transactions, time_period)
            
            if sankey_type == "Income → Categories → Subcategories":
                self._create_income_category_sankey(filtered_transactions)
            elif sankey_type == "Monthly Flow":
                self._create_monthly_flow_sankey(filtered_transactions)
            else:
                self._create_category_hierarchy_sankey(filtered_transactions)
                
        except ImportError:
            st.error("Plotly is required for Sankey diagrams. Please install plotly.")
        except Exception as e:
            st.error(f"Error creating Sankey diagram: {e}")
            self.logger.error(f"Sankey diagram error: {e}")
    
    def _filter_transactions_by_period(self, transactions, period):
        """Filter transactions by time period."""
        if period == "All Time":
            return transactions
        
        from datetime import datetime, timedelta
        today = datetime.now()
        
        if period == "Last 3 Months":
            cutoff = today - timedelta(days=90)
        elif period == "Last 6 Months":
            cutoff = today - timedelta(days=180)
        elif period == "This Year":
            cutoff = datetime(today.year, 1, 1)
        else:
            return transactions
        
        return [t for t in transactions if t.transaction_date >= cutoff]
    
    def _create_income_category_sankey(self, transactions):
        """Create Sankey diagram showing income flow to categories."""
        import plotly.graph_objects as go
        
        # Separate income and expenses
        income_transactions = [t for t in transactions if t.is_payment()]
        expense_transactions = [t for t in transactions if t.is_expense()]
        
        if not income_transactions or not expense_transactions:
            st.info("Need both income and expense transactions for this Sankey diagram.")
            return
        
        # Calculate totals
        total_income = sum(t.amount for t in income_transactions)
        
        # Group expenses by category
        category_expenses = {}
        for t in expense_transactions:
            category_expenses[t.category] = category_expenses.get(t.category, 0) + abs(t.amount)
        
        # Create nodes and links
        nodes = ["Income"] + list(category_expenses.keys())
        node_colors = ["#2E8B57"] + ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE"][:len(category_expenses)]
        
        # Create links from income to categories
        sources = [0] * len(category_expenses)  # All from "Income"
        targets = list(range(1, len(category_expenses) + 1))  # To each category
        values = list(category_expenses.values())
        
        # Create Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=nodes,
                color=node_colors
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=["rgba(255,107,107,0.3)"] * len(values)
            )
        )])
        
        fig.update_layout(
            title_text="Money Flow: Income → Spending Categories",
            font_size=12,
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True, key="income_category_sankey")
        
        # Show summary
        st.write("**Summary:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Income", f"${total_income:.2f}")
        with col2:
            st.metric("Total Expenses", f"${sum(category_expenses.values()):.2f}")
        with col3:
            st.metric("Net Amount", f"${total_income - sum(category_expenses.values()):.2f}")
    
    def _create_monthly_flow_sankey(self, transactions):
        """Create Sankey diagram showing monthly money flow."""
        import plotly.graph_objects as go
        
        # Group transactions by month and category
        monthly_data = {}
        for t in transactions:
            month_key = t.transaction_date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {}
            
            category = t.category
            if category not in monthly_data[month_key]:
                monthly_data[month_key][category] = 0
            
            monthly_data[month_key][category] += abs(t.amount) if t.is_expense() else 0
        
        if len(monthly_data) < 2:
            st.info("Need at least 2 months of data for monthly flow Sankey diagram.")
            return
        
        # Create nodes (months + categories)
        months = sorted(monthly_data.keys())[-6:]  # Last 6 months
        all_categories = set()
        for month_data in monthly_data.values():
            all_categories.update(month_data.keys())
        
        nodes = months + list(all_categories)
        
        # Create links
        sources = []
        targets = []
        values = []
        
        for i, month in enumerate(months):
            for category, amount in monthly_data[month].items():
                if amount > 0:
                    sources.append(i)  # Month index
                    targets.append(len(months) + list(all_categories).index(category))  # Category index
                    values.append(amount)
        
        if not sources:
            st.info("No expense data available for monthly flow diagram.")
            return
        
        # Create Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=nodes,
                color=["#4ECDC4"] * len(months) + ["#FF6B6B"] * len(all_categories)
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values
            )
        )])
        
        fig.update_layout(
            title_text="Monthly Money Flow to Categories",
            font_size=12,
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True, key="monthly_flow_sankey")
    
    def _create_category_hierarchy_sankey(self, transactions):
        """Create Sankey diagram showing category hierarchy."""
        import plotly.graph_objects as go
        
        # Get category hierarchy
        hierarchy = self.db.get_category_hierarchy()
        
        if not hierarchy:
            st.info("No category hierarchy defined. Set up category relationships first.")
            
            # Show category hierarchy management
            self._show_category_hierarchy_management()
            return
        
        # Calculate amounts for each category
        category_amounts = {}
        for t in transactions:
            if t.is_expense():
                category_amounts[t.category] = category_amounts.get(t.category, 0) + abs(t.amount)
        
        # Create nodes and links based on hierarchy
        nodes = []
        sources = []
        targets = []
        values = []
        
        # Add root categories first
        root_categories = [cat for cat, info in hierarchy.items() if info['parent'] is None]
        
        for root_cat in root_categories:
            if root_cat not in nodes:
                nodes.append(root_cat)
            
            # Add children
            for child in hierarchy[root_cat]['children']:
                if child not in nodes:
                    nodes.append(child)
                
                # Create link from parent to child
                if child in category_amounts:
                    sources.append(nodes.index(root_cat))
                    targets.append(nodes.index(child))
                    values.append(category_amounts[child])
        
        if not sources:
            st.info("No hierarchical relationships found with transaction data.")
            return
        
        # Create Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=nodes,
                color=["#45B7D1"] * len(nodes)
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values
            )
        )])
        
        fig.update_layout(
            title_text="Category Hierarchy Money Flow",
            font_size=12,
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True, key="hierarchy_sankey")
    
    def _show_category_hierarchy_management(self):
        """Show interface for managing category hierarchy."""
        st.subheader("🏗️ Category Hierarchy Management")
        
        # Get existing categories
        existing_categories = self.db.get_categories()
        hierarchy = self.db.get_category_hierarchy()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Add Category Relationship**")
            
            child_category = st.selectbox(
                "Child Category",
                existing_categories,
                key="hierarchy_child"
            )
            
            parent_options = ["None (Root Category)"] + [cat for cat in existing_categories if cat != child_category]
            parent_category = st.selectbox(
                "Parent Category",
                parent_options,
                key="hierarchy_parent"
            )
            
            if st.button("Add Relationship", key="add_hierarchy"):
                parent = None if parent_category == "None (Root Category)" else parent_category
                success = self.db.add_category_hierarchy(child_category, parent)
                
                if success:
                    st.success(f"✅ Added '{child_category}' under '{parent_category}'")
                    st.experimental_rerun()
                else:
                    st.error("❌ Failed to add relationship")
        
        with col2:
            st.write("**Current Hierarchy**")
            
            if hierarchy:
                # Display hierarchy as tree
                root_categories = [cat for cat, info in hierarchy.items() if info['parent'] is None]
                
                for root_cat in root_categories:
                    st.write(f"📁 **{root_cat}**")
                    self._display_category_tree(root_cat, hierarchy, level=1)
            else:
                st.info("No hierarchy defined yet.")
    
    def _display_category_tree(self, category, hierarchy, level=0):
        """Recursively display category tree."""
        indent = "  " * level
        
        if category in hierarchy:
            for child in hierarchy[category]['children']:
                st.write(f"{indent}├── {child}")
                self._display_category_tree(child, hierarchy, level + 1)
    
    def _show_category_hierarchy_view(self):
        """Show the current category hierarchy in a readable format."""
        hierarchy = self.db.get_category_hierarchy()
        
        if not hierarchy:
            st.info("No category hierarchy has been set up yet. Use the 'Manage Hierarchy' tab to create relationships between categories.")
            return
        
        # Show hierarchy statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_categories = len(hierarchy)
            st.metric("Total Categories", total_categories)
        
        with col2:
            root_categories = len([cat for cat, info in hierarchy.items() if info['parent'] is None])
            st.metric("Root Categories", root_categories)
        
        with col3:
            max_level = max(info['level'] for info in hierarchy.values()) if hierarchy else 0
            st.metric("Max Depth", max_level + 1)
        
        # Display hierarchy tree
        st.write("**Category Tree:**")
        
        root_categories = [cat for cat, info in hierarchy.items() if info['parent'] is None]
        
        if root_categories:
            for root_cat in root_categories:
                # Get transaction count for this category and its children
                category_transactions = self.db.get_transactions_by_category_hierarchy(root_cat, include_children=True)
                transaction_count = len(category_transactions)
                total_amount = sum(abs(t.amount) for t in category_transactions if t.is_expense())
                
                st.write(f"📁 **{root_cat}** ({transaction_count} transactions, ${total_amount:.2f})")
                self._display_category_tree_with_stats(root_cat, hierarchy, level=1)
        else:
            st.info("All categories are at root level (no hierarchy defined).")
    
    def _display_category_tree_with_stats(self, category, hierarchy, level=0):
        """Display category tree with transaction statistics."""
        indent = "  " * level
        
        if category in hierarchy:
            for child in hierarchy[category]['children']:
                # Get stats for this child category
                child_transactions = self.db.get_transactions_by_category_hierarchy(child, include_children=False)
                transaction_count = len(child_transactions)
                total_amount = sum(abs(t.amount) for t in child_transactions if t.is_expense())
                
                st.write(f"{indent}├── {child} ({transaction_count} transactions, ${total_amount:.2f})")
                self._display_category_tree_with_stats(child, hierarchy, level + 1)
    
    def _create_database_backup(self, backup_name: str):
        """Create a backup of the current database."""
        try:
            import shutil
            import os
            from pathlib import Path
            
            # Create backups directory
            backup_dir = Path("data/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backup filename
            backup_filename = f"{backup_name}.db"
            backup_path = backup_dir / backup_filename
            
            # Copy database file
            shutil.copy2(self.db.db_path, backup_path)
            
            # Create download link
            with open(backup_path, 'rb') as f:
                backup_data = f.read()
            
            st.success(f"✅ Database backup created successfully!")
            st.download_button(
                label="📥 Download Database Backup",
                data=backup_data,
                file_name=backup_filename,
                mime="application/octet-stream",
                key="download_db_backup"
            )
            
            # Show backup info
            backup_size = len(backup_data) / (1024 * 1024)  # MB
            st.info(f"Database backup size: {backup_size:.2f} MB")
            
        except Exception as e:
            st.error(f"❌ Failed to create database backup: {e}")
            self.logger.error(f"Database backup creation failed: {e}")
    
    def _restore_database_backup(self, uploaded_backup):
        """Restore database from uploaded backup."""
        try:
            import tempfile
            import shutil
            
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
                tmp_file.write(uploaded_backup.read())
                tmp_path = tmp_file.name
            
            # Validate the backup file (basic SQLite check)
            try:
                import sqlite3
                with sqlite3.connect(tmp_path) as conn:
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
                    if not cursor.fetchone():
                        st.error("❌ Invalid backup file: missing transactions table")
                        return
            except sqlite3.Error as e:
                st.error(f"❌ Invalid backup file: {e}")
                return
            
            # Create backup of current database before restore
            current_backup_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._create_database_backup(current_backup_name)
            
            # Replace current database
            shutil.copy2(tmp_path, self.db.db_path)
            
            # Clean up temporary file
            import os
            os.unlink(tmp_path)
            
            st.success("✅ Database restored successfully!")
            st.info("Your previous database was backed up before restoration.")
            
            # Reload data
            self._load_data()
            st.experimental_rerun()
            
        except Exception as e:
            st.error(f"❌ Failed to restore backup: {e}")
            self.logger.error(f"Backup restoration failed: {e}")
            return False