"""Performance monitoring and optimization utilities."""

import time
import logging
from functools import wraps
from typing import Any, Callable, Dict
import streamlit as st


class PerformanceMonitor:
    """Monitor and log performance metrics."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics = {}
    
    def time_operation(self, operation_name: str):
        """Decorator to time operations."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Log performance
                    self.logger.info(f"Operation '{operation_name}' took {execution_time:.3f}s")
                    
                    # Store metrics
                    if operation_name not in self.metrics:
                        self.metrics[operation_name] = []
                    self.metrics[operation_name].append(execution_time)
                    
                    # Show warning for slow operations
                    if execution_time > 2.0:
                        self.logger.warning(f"Slow operation detected: '{operation_name}' took {execution_time:.3f}s")
                    
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.logger.error(f"Operation '{operation_name}' failed after {execution_time:.3f}s: {e}")
                    raise
            return wrapper
        return decorator
    
    def get_metrics_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of performance metrics."""
        summary = {}
        for operation, times in self.metrics.items():
            if times:
                summary[operation] = {
                    'count': len(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'total_time': sum(times)
                }
        return summary


# Global performance monitor instance
perf_monitor = PerformanceMonitor()


class StreamlitCache:
    """Streamlit-specific caching utilities."""
    
    @staticmethod
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_cached_category_stats(db_path: str) -> Dict[str, Any]:
        """Cache category statistics for better performance."""
        from app.db import DatabaseManager
        db = DatabaseManager(db_path)
        return db.get_category_stats_optimized()
    
    @staticmethod
    @st.cache_data(ttl=60)  # Cache for 1 minute
    def get_cached_categories(db_path: str) -> list:
        """Cache categories list for better performance."""
        from app.db import DatabaseManager
        db = DatabaseManager(db_path)
        return db.get_categories()
    
    @staticmethod
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_cached_transaction_count(db_path: str) -> int:
        """Cache transaction count for better performance."""
        from app.db import DatabaseManager
        db = DatabaseManager(db_path)
        return db.get_transaction_count()
    
    @staticmethod
    def clear_all_cache():
        """Clear all Streamlit cache."""
        st.cache_data.clear()


def show_performance_metrics():
    """Display performance metrics in Streamlit."""
    metrics = perf_monitor.get_metrics_summary()
    
    if not metrics:
        st.info("No performance metrics available yet.")
        return
    
    st.subheader("⚡ Performance Metrics")
    
    for operation, stats in metrics.items():
        with st.expander(f"📊 {operation}"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Executions", stats['count'])
            with col2:
                st.metric("Avg Time", f"{stats['avg_time']:.3f}s")
            with col3:
                st.metric("Min Time", f"{stats['min_time']:.3f}s")
            with col4:
                st.metric("Max Time", f"{stats['max_time']:.3f}s")
            
            # Performance status
            if stats['avg_time'] > 2.0:
                st.error("⚠️ This operation is running slowly")
            elif stats['avg_time'] > 1.0:
                st.warning("⚠️ This operation could be optimized")
            else:
                st.success("✅ This operation is performing well")


def optimize_large_dataset_display(data: list, page_size: int = 50) -> tuple:
    """Optimize display of large datasets with pagination."""
    total_items = len(data)
    
    if total_items <= page_size:
        return data, 1, 1
    
    # Initialize pagination in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    total_pages = (total_items + page_size - 1) // page_size
    current_page = st.session_state.current_page
    
    # Ensure current page is valid
    if current_page > total_pages:
        st.session_state.current_page = total_pages
        current_page = total_pages
    
    # Calculate slice indices
    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    
    # Return paginated data
    return data[start_idx:end_idx], current_page, total_pages


def show_pagination_controls(current_page: int, total_pages: int, total_items: int):
    """Show pagination controls for large datasets."""
    if total_pages <= 1:
        return
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("⏮️ First", disabled=current_page == 1, key="page_first"):
            st.session_state.current_page = 1
            st.rerun()
    
    with col2:
        if st.button("◀️ Prev", disabled=current_page == 1, key="page_prev"):
            st.session_state.current_page = current_page - 1
            st.rerun()
    
    with col3:
        st.write(f"Page {current_page} of {total_pages} ({total_items} total items)")
    
    with col4:
        if st.button("Next ▶️", disabled=current_page >= total_pages, key="page_next"):
            st.session_state.current_page = current_page + 1
            st.rerun()
    
    with col5:
        if st.button("Last ⏭️", disabled=current_page >= total_pages, key="page_last"):
            st.session_state.current_page = total_pages
            st.rerun()


def optimize_chart_data(data: list, max_points: int = 1000) -> list:
    """Optimize chart data for better rendering performance."""
    if len(data) <= max_points:
        return data
    
    # Sample data points for better performance
    step = len(data) // max_points
    return data[::step]