import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from tefas import Crawler
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this for production

# --- Configuration ---
# Scope for Google Sheets API
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_google_sheet_client():
    """
    Connects to Google Sheets using credentials from environment variable or file.
    For this example, we expect a 'credentials.json' file in the root or 
    GOOGLE_CREDENTIALS env var containing the JSON string.
    """
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    elif os.path.exists('credentials.json'):
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPE)
    else:
        return None
        
    client = gspread.authorize(creds)
    return client

def get_tefas_data(fund_codes):
    """
    Fetches current data for the given fund codes using tefas-crawler.
    """
    if not fund_codes:
        return {}
    
    crawler = Crawler()
    # Fetch data for today (or recent past if today is weekend/holiday)
    # tefas-crawler usually fetches a range. We'll fetch last 3 days to ensure we get latest price.
    # Note: tefas-crawler usage might vary slightly by version, this is a standard approach.
    
    try:
        # Fetching latest data. 
        # We will just fetch general info to get the latest price.
        # Ideally we want 'Price' for specific funds.
        # The crawler returns a DataFrame.
        
        # Let's fetch data for the specific funds. 
        # Since tefas-crawler fetches by date range, we get the latest available.
        start_date = (datetime.now() - pd.Timedelta(days=5)).strftime('%Y-%m-%d')
        
        # This fetches all funds, then we filter. Efficient enough for this scale.
        df = crawler.fetch(start=start_date, columns=["code", "price", "title"])
        
        # Get the latest date in the dataset
        latest_date = df['date'].max()
        latest_df = df[df['date'] == latest_date]
        
        # Create a dictionary: { 'ABC': {'price': 1.23, 'title': '...'} }
        result = {}
        for code in fund_codes:
            fund_row = latest_df[latest_df['code'] == code]
            if not fund_row.empty:
                result[code] = {
                    'price': float(fund_row.iloc[0]['price']),
                    'title': fund_row.iloc[0]['title']
                }
            else:
                # Fallback or 0 if not found
                result[code] = {'price': 0.0, 'title': code}
                
        return result
    except Exception as e:
        print(f"Error fetching TEFAS data: {e}")
        return {}

def calculate_portfolio(transactions, current_prices):
    """
    Calculates weighted average cost and current value.
    transactions: list of dicts [{'Code': 'AFT', 'Date': '...', 'Amount': 1000, 'Price': 2.5}, ...]
    """
    portfolio = {}
    
    # Group by fund code
    for t in transactions:
        code = t.get('Code', '').upper()
        if not code: continue
        
        try:
            qty = float(t.get('Quantity', 0)) # Number of shares
            price = float(t.get('Price', 0))  # Purchase price
        except ValueError:
            continue
            
        if code not in portfolio:
            portfolio[code] = {
                'total_qty': 0.0,
                'total_cost': 0.0,
                'avg_cost': 0.0
            }
            
        # Weighted Average Calculation
        # New Total Cost = Old Total Cost + (New Qty * New Price)
        # New Total Qty = Old Total Qty + New Qty
        # Avg Cost = New Total Cost / New Total Qty
        
        # Handle Sell (negative quantity) if needed, but assuming Buy only for simplicity or simple logic
        # If selling, we reduce quantity but Avg Cost stays same (FIFO/Weighted logic varies).
        # For this simple tracker, let's assume simple weighted average accumulation.
        
        portfolio[code]['total_qty'] += qty
        portfolio[code]['total_cost'] += (qty * price)
        
    # Finalize calculations
    summary = []
    total_portfolio_value = 0.0
    total_invested = 0.0
    
    for code, data in portfolio.items():
        if data['total_qty'] == 0:
            continue
            
        data['avg_cost'] = data['total_cost'] / data['total_qty']
        
        current_info = current_prices.get(code, {'price': 0, 'title': code})
        current_price = current_info['price']
        title = current_info['title']
        
        current_value = data['total_qty'] * current_price
        profit_loss = current_value - data['total_cost']
        profit_loss_pct = (profit_loss / data['total_cost']) * 100 if data['total_cost'] > 0 else 0
        
        total_portfolio_value += current_value
        total_invested += data['total_cost']
        
        summary.append({
            'code': code,
            'title': title,
            'quantity': data['total_qty'],
            'avg_cost': data['avg_cost'],
            'current_price': current_price,
            'total_cost': data['total_cost'],
            'current_value': current_value,
            'profit_loss': profit_loss,
            'profit_loss_pct': profit_loss_pct
        })
        
    return summary, total_portfolio_value, total_invested

# --- Routes ---

@app.route('/')
def index():
    client = get_google_sheet_client()
    if not client:
        return "Google Credentials not found. Please configure credentials.json or env var."
    
    try:
        # Open the sheet. We assume the sheet is named 'Portfolio'
        # You might need to share your sheet with the client_email in credentials.json
        sheet = client.open("Portfolio").sheet1
        records = sheet.get_all_records()
    except Exception as e:
        return f"Error connecting to Google Sheet: {e}. Make sure you shared the sheet 'Portfolio' with the service account email."

    # Get unique fund codes to fetch prices
    fund_codes = list(set([r.get('Code').upper() for r in records if r.get('Code')]))
    
    # Fetch live prices
    current_prices = get_tefas_data(fund_codes)
    
    # Calculate portfolio
    portfolio_data, total_val, total_inv = calculate_portfolio(records, current_prices)
    
    net_profit = total_val - total_inv
    net_profit_pct = (net_profit / total_inv * 100) if total_inv > 0 else 0
    
    # Prepare data for Chart.js
    chart_labels = [item['code'] for item in portfolio_data]
    chart_data = [item['current_value'] for item in portfolio_data]
    
    return render_template('index.html', 
                           portfolio=portfolio_data,
                           total_value=total_val,
                           total_invested=total_inv,
                           net_profit=net_profit,
                           net_profit_pct=net_profit_pct,
                           chart_labels=chart_labels,
                           chart_data=chart_data)

@app.route('/add', methods=['POST'])
def add_transaction():
    client = get_google_sheet_client()
    if not client:
        return "Credentials Error"
        
    code = request.form.get('code').upper()
    date = request.form.get('date')
    quantity = request.form.get('quantity')
    price = request.form.get('price')
    
    if code and date and quantity and price:
        try:
            sheet = client.open("Portfolio").sheet1
            # Append row: Code, Date, Quantity, Price
            sheet.append_row([code, date, float(quantity), float(price)])
            flash('Transaction added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding transaction: {e}', 'danger')
            
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
