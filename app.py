import os
import pandas as pd
import numpy as np
import time
from datetime import datetime
import yfinance as yf
import sqlite3
import threading
from flask import Flask, render_template, jsonify
import logging
import asyncio
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleNiftyAnalyzer:
    def __init__(self):
        self.nifty_symbols = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
            "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
            "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS",
            "TITAN.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS"
        ]
        
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # Initialize database
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect('nifty_analysis.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                signal_type TEXT,
                strength TEXT,
                price REAL,
                timestamp DATETIME,
                description TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def fetch_stock_data(self, symbol: str):
        """Fetch stock data using yfinance"""
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period="30d")
            if data.empty:
                return None
            return data
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1]
        except:
            return 50
    
    def analyze_stock(self, symbol):
        """Simple analysis for one stock"""
        try:
            data = self.fetch_stock_data(symbol)
            if data is None or data.empty:
                return None
            
            current_price = data['Close'].iloc[-1]
            rsi = self.calculate_rsi(data['Close'])
            
            # Simple RSI-based signals
            if rsi < 30:
                return {
                    'symbol': symbol,
                    'signal_type': 'BUY',
                    'strength': 'STRONG',
                    'price': current_price,
                    'description': f'RSI Oversold: {rsi:.2f}',
                    'timestamp': datetime.now()
                }
            elif rsi > 70:
                return {
                    'symbol': symbol,
                    'signal_type': 'SELL',
                    'strength': 'STRONG',
                    'price': current_price,
                    'description': f'RSI Overbought: {rsi:.2f}',
                    'timestamp': datetime.now()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def save_signal_to_db(self, signal):
        """Save signal to database"""
        if not signal:
            return
            
        conn = sqlite3.connect('nifty_analysis.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO analysis_results (symbol, signal_type, strength, price, timestamp, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (signal['symbol'], signal['signal_type'], signal['strength'], 
              signal['price'], signal['timestamp'], signal['description']))
        
        conn.commit()
        conn.close()
    
    def send_telegram_message(self, message):
        """Send message to Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram not configured")
            return
            
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
            else:
                logger.error(f"Telegram error: {response.text}")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
    
    def analyze_nifty_50(self):
        """Main analysis function"""
        logger.info("Starting Nifty 50 analysis...")
        signals = []
        
        for symbol in self.nifty_symbols[:10]:  # Limit to 10 for faster execution
            try:
                signal = self.analyze_stock(symbol)
                if signal:
                    signals.append(signal)
                    self.save_signal_to_db(signal)
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
        
        if signals:
            message = self.format_signals_message(signals)
            self.send_telegram_message(message)
            
        logger.info(f"Analysis complete. Found {len(signals)} signals.")
        return signals
    
    def format_signals_message(self, signals):
        """Format signals for Telegram"""
        if not signals:
            return "🔍 <b>Nifty 50 Analysis</b>\n\nNo significant signals detected."
        
        message = "🚀 <b>Nifty 50 Technical Signals</b>\n\n"
        
        for signal in signals:
            symbol_clean = signal['symbol'].replace(".NS", "")
            emoji = "📈" if signal['signal_type'] == "BUY" else "📉"
            message += f"{emoji} <b>{symbol_clean}</b> - ₹{signal['price']:.2f}\n"
            message += f"📝 {signal['description']}\n\n"
        
        message += f"⏰ <i>Updated: {datetime.now().strftime('%d/%m/%Y %H:%M IST')}</i>"
        return message

# Flask Web Interface
app = Flask(__name__)
analyzer = SimpleNiftyAnalyzer()

@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/latest-signals')
def get_latest_signals():
    """API endpoint for latest signals"""
    try:
        conn = sqlite3.connect('nifty_analysis.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, signal_type, strength, price, timestamp, description
            FROM analysis_results
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in results:
            signals.append({
                'symbol': row[0].replace('.NS', ''),
                'signal_type': row[1],
                'strength': row[2],
                'price': row[3],
                'timestamp': row[4],
                'description': row[5]
            })
        
        return jsonify(signals)
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify([])

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

def run_analysis_loop():
    """Run analysis in background"""
    while True:
        try:
            analyzer.analyze_nifty_50()
            time.sleep(900)  # 15 minutes
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            time.sleep(60)  # Wait 1 minute on error

def main():
    """Main function"""
    # Start background analysis
    analysis_thread = threading.Thread(target=run_analysis_loop, daemon=True)
    analysis_thread.start()
    
    # Run initial analysis
    try:
        analyzer.analyze_nifty_50()
    except Exception as e:
        logger.error(f"Initial analysis error: {e}")
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()
