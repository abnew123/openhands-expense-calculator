#!/bin/bash
set -e

# Create data directory if it doesn't exist
mkdir -p /app/data

# Set proper permissions
chown -R appuser:appuser /app/data

# Run database initialization check
echo "Checking database initialization..."
python -c "from app.db import DatabaseManager; db = DatabaseManager(); print('Database initialized successfully')"

# Start the application
echo "Starting Expense Tracker application..."
exec streamlit run run_app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false