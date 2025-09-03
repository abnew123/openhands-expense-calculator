# Supported CSV Formats

This directory contains sample CSV files for each supported bank format. These files demonstrate the expected column structure and data format for successful imports.

## Supported Formats

### Chase Credit Card (`chase_sample.csv`)
- **Columns**: Transaction Date, Post Date, Description, Category, Type, Amount, Memo
- **Date Format**: MM/DD/YYYY
- **Notes**: Full-featured format with separate transaction and post dates

### American Express (`american_express_sample.csv`)
- **Columns**: Date, Description, Amount
- **Date Format**: MM/DD/YYYY
- **Notes**: Simple 3-column format

### Bank of America (`bank_of_america_sample.csv`)
- **Columns**: Date, Description, Amount, Running Bal.
- **Date Format**: MM/DD/YYYY
- **Notes**: Includes running balance column

### Wells Fargo (`wells_fargo_sample.csv`)
- **Columns**: Date, Amount, Description
- **Date Format**: MM/DD/YYYY
- **Notes**: 3-column format with amount before description

### Wells Fargo (No Headers) (`wells_fargo_headerless_sample.csv`)
- **Columns**: Date, Amount, Description (no header row)
- **Date Format**: MM/DD/YYYY
- **Notes**: Same as Wells Fargo but without column headers

### Capital One (`capital_one_sample.csv`)
- **Columns**: Transaction Date, Posted Date, Card No., Description, Category, Debit, Credit
- **Date Format**: MM/DD/YYYY
- **Notes**: Uses separate Debit and Credit columns instead of signed amounts

## Usage

1. Download your bank's CSV export
2. Compare the format with the appropriate sample file
3. Upload to the expense tracker using the CSV import feature
4. The application will automatically detect the format and import your transactions

## Data Standardization

Each sample file contains:
- **Positive Amount**: Deposit/Payment (income)
- **Negative Amount**: Payment/Withdrawal (expense)
- **Consistent Naming**: Format name + "Deposit" or "Payment"
- **Standard Dates**: 01/15/2024 and 01/17/2024 for consistency