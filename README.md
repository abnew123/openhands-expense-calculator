# 💰 Personal Expense Tracker

A comprehensive, local-first expense tracking application that helps you manage and visualize your credit card transactions. Upload your Chase credit card CSV files and get instant insights into your spending patterns with advanced analytics, category management, and filtering capabilities.

## ✨ Features

- 📊 **Interactive Dashboard** with real-time metrics and visualizations
- 📁 **CSV Upload** with duplicate detection and preview
- 🔍 **Advanced Search & Filtering** with date presets and custom ranges
- 🏷️ **Smart Category Management** with auto-categorization and bulk editing
- 📈 **Comprehensive Analytics** with multiple chart types and export options
- 🔒 **Privacy-First** - all data stays local, no cloud dependencies
- 🐳 **Docker Support** for easy deployment
- 🧪 **Fully Tested** with comprehensive test suite

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Using Docker Compose
docker-compose up -d

# Or using Docker directly
docker run -d -p 8501:8501 -v $(pwd)/data:/app/data expense-tracker
```

Access the application at `http://localhost:8501`

### Option 2: Local Python Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start the application
streamlit run run_app.py
```

**New to the application?** Check out our [Quick Start Guide](QUICK_START.md) for detailed setup instructions!

## 📱 How to Use the Expense Tracker

### Getting Your Chase CSV File
1. Log into your Chase online banking
2. Go to your credit card account
3. Click "Download account activity" or "Export transactions"
4. Select CSV format and your desired date range
5. Download the file to your computer

### Using the Application

#### 1. **Dashboard** 📊
- See your spending overview with key metrics
- View recent transactions at a glance
- Get a quick summary of expenses vs payments

#### 2. **Upload CSV** 📁
- **Drag and drop** your Chase CSV file or click "Browse files"
- **Preview** your transactions before importing
- The app automatically **prevents duplicates** if you upload the same file twice
- Get confirmation of how many new transactions were added

#### 3. **View Transactions** 📋
- **Advanced Table** with search, sorting, and pagination
- **Smart Filtering** with date presets (This Month, Last 3 Months, etc.)
- **Amount Range Filtering** with interactive sliders
- **Bulk Category Editing** for multiple transactions at once
- **Export Options** for filtered data

#### 4. **Category Management** 🏷️
- **Dedicated Categories Page** for comprehensive management
- **Category Statistics** showing transaction counts and totals
- **Rename, Merge, and Delete** categories with transaction preservation
- **Auto-Categorization** using intelligent pattern matching
- **Bulk Operations** for efficient category organization

#### 5. **Enhanced Analytics** 📈
- **Multiple Chart Types**: Pie charts, bar charts, histograms, and trends
- **Interactive Visualizations** with hover details and click-to-filter
- **Spending Analysis**: By category, time, day of week, and amount distribution
- **Payment Tracking**: Separate analysis for payments and expenses
- **Export Functionality**: Save charts in PNG, HTML, or SVG formats

## 💡 Tips for Best Results

### Organizing Your Transactions
- **Review Categories**: After uploading, review and update categories to match your spending habits
- **Consistent Naming**: Use consistent category names (e.g., always "Food" not sometimes "Food & Drink")
- **Regular Updates**: Upload new CSV files monthly to keep your data current

### Understanding Your Data
- **Negative Amounts**: Expenses show as negative numbers (e.g., -$50.00)
- **Positive Amounts**: Payments show as positive numbers (e.g., +$200.00)
- **Date Format**: All dates are shown as YYYY-MM-DD for consistency

### Getting the Most from Analytics
- **Monthly View**: Use date filters to compare spending across different months
- **Category Analysis**: Use the pie chart to identify your biggest spending categories
- **Trend Tracking**: Use the time series chart to spot spending patterns

## 🔧 Troubleshooting

### Common Issues

**"Module not found" error when starting**
```bash
# Make sure you installed the requirements
pip install -r requirements.txt
```

**"Port already in use" error**
- Close any other applications using port 8501
- Or edit `run_app.py` and change the port number

**CSV upload not working**
- Make sure your file is a Chase credit card CSV export
- Check that the file has these columns: Transaction Date, Post Date, Description, Category, Type, Amount, Memo

**Application won't start**
- Make sure you have Python 3.8 or newer installed
- Try running: `python --version` to check your Python version

### Getting Help
- Check the `HANDOFF.md` file for technical details
- Look at `expense_tracker.log` for error messages
- Sample CSV files are included in the `supported_formats/` folder

## 🔒 Privacy & Security

### Your Data Stays Local
- **No Internet Required**: All data is stored locally on your computer
- **No Cloud Storage**: Your financial data never leaves your device
- **SQLite Database**: Data is stored in a local `expenses.db` file
- **No Tracking**: The application doesn't send any data anywhere

### Data Storage
- **Database Location**: `expenses.db` file in the application folder
- **Backup**: You can copy this file to backup your data
- **Reset**: Delete `expenses.db` to start fresh (all data will be lost)

## 📋 Supported File Formats

Currently supports:
- **Chase Credit Card CSV** exports from Chase online banking

The CSV file should have these columns:
- Transaction Date
- Post Date  
- Description
- Category
- Type
- Amount
- Memo

## 🛠️ Advanced Usage

### Docker Deployment

For production deployment with Docker:

```bash
# Build the image
docker build -t expense-tracker .

# Run with custom configuration
docker run -d \
  --name expense-tracker \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -e STREAMLIT_SERVER_PORT=8501 \
  expense-tracker
```

See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for comprehensive Docker deployment guide.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run with development settings
streamlit run run_app.py --server.runOnSave=true
```

### Configuration Options

Environment variables for customization:

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAMLIT_SERVER_PORT` | `8501` | Application port |
| `STREAMLIT_SERVER_ADDRESS` | `localhost` | Bind address |
| `DATABASE_PATH` | `data/expenses.db` | Database file location |

### Data Management

- **Database Location**: `data/expenses.db` (or `expenses.db` for local installs)
- **Backup**: Copy the database file to create backups
- **Migration**: Database schema updates are handled automatically
- **Export**: Use the built-in export features or access SQLite directly

## 🧪 Testing

The application includes a comprehensive test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_models.py -v
pytest tests/test_database.py -v
pytest tests/test_integration.py -v
```

## 🔄 Updates and Maintenance

### Keeping Your Data Safe
- **Automatic Backups**: Database is stored in persistent `data/` directory
- **Version Control**: Database schema migrations are handled automatically
- **Export Options**: Use built-in export features for additional backups

### Getting Updates

**Docker Deployment:**
```bash
docker-compose pull
docker-compose up -d
```

**Local Installation:**
```bash
git pull origin main
pip install -r requirements.txt
streamlit run run_app.py
```

## 📊 Project Status

- **Current Version**: Enhanced MVP (9/13 tickets completed)
- **Test Coverage**: 44 tests covering all major functionality
- **Docker Ready**: Full containerization with health checks
- **Production Ready**: Suitable for personal and small business use

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `pytest tests/ -v`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

- **Documentation**: Check [HANDOFF.md](HANDOFF.md) for technical details
- **Docker Issues**: See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)
- **Quick Start**: Follow [QUICK_START.md](QUICK_START.md) for setup help
- **Issues**: Report bugs and feature requests on GitHub

**Enjoy tracking your expenses with advanced analytics!** 💰📊✨