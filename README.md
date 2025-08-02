# 💰 Personal Expense Tracker

A simple, local expense tracking application that helps you manage and visualize your credit card transactions. Upload your Chase credit card CSV files and get instant insights into your spending patterns.

## 🚀 Quick Start

### What You Need
- A computer with Python installed (Windows, Mac, or Linux)
- Your Chase credit card CSV file (downloaded from Chase online banking)

### Step 1: Download the Application
1. Click the green "Code" button above and select "Download ZIP"
2. Extract the ZIP file to a folder on your computer
3. Open a terminal/command prompt and navigate to the folder

### Step 2: Install Required Software
```bash
# Install the required packages
pip install -r requirements.txt
```

### Step 3: Run the Application
```bash
# Start the expense tracker
python run_app.py
```

The application will start and automatically open in your web browser at `http://localhost:8501`

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
- See all your transactions in a sortable table
- **Filter by date range** using the date picker
- **Filter by category** (Food, Shopping, etc.) or transaction type
- **Search** for specific transactions
- Click on any column header to sort

#### 4. **Edit Categories** ✏️
- Change transaction categories to better organize your spending
- Select a transaction from the dropdown
- Choose a new category from the list
- Changes are saved automatically

#### 5. **Analytics** 📈
- **Pie Chart**: See spending breakdown by category
- **Bar Chart**: View monthly spending trends
- **Time Series**: Track spending patterns over time
- All charts are interactive - hover for details, zoom, and pan

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

### Running on a Different Port
Edit `run_app.py` and change the port number:
```python
if __name__ == "__main__":
    main(port=8502)  # Change to your preferred port
```

### Accessing from Other Devices
To access the tracker from other devices on your network:
1. Find your computer's IP address
2. Start the application with: `streamlit run run_app.py --server.address 0.0.0.0`
3. Access from other devices using: `http://YOUR_IP_ADDRESS:8501`

### Data Export
Your data is stored in SQLite format. You can:
- Use any SQLite browser to view the raw data
- The database file is located at `expenses.db`
- Future versions will include CSV export functionality

## 🔄 Updates and Maintenance

### Keeping Your Data Safe
- **Regular Backups**: Copy the `expenses.db` file to a safe location
- **Before Updates**: Always backup your database before updating the application

### Getting Updates
1. Download the latest version from GitHub
2. Copy your `expenses.db` file to the new version folder
3. Install any new requirements: `pip install -r requirements.txt`

---

## 📞 Support

For technical issues or feature requests, please check the GitHub issues page or refer to the `HANDOFF.md` file for developer information.

**Enjoy tracking your expenses!** 💰📊