import os
import time
from datetime import datetime
import yfinance as yf
import sqlite3
import threading
from flask import Flask, render_template, jsonify
import logging
import requests
import warnings
import json

# Suppress warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleNiftyAnalyzer:
    def __init__(self):
        # Top 15 Nifty stocks for faster processing
        self.nifty_symbols = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", 
            "HINDUNILVR.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS",
            "ITC.NS", "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS",
            "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS"
        ]
        
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # Initialize database
        self.init_database()
        logger.info("SimpleNiftyAnalyzer initialized successfully")
        
    def init_database(self):
        """Initialize SQLite database"""
        try:
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
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
        
    def fetch_stock_data(self, symbol: str):
        """Fetch stock data using yfinance"""
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period="30d", timeout=15)
            
            if data.empty:
                logger.warning(f"No data found for {symbol}")
                return None
                
            return data
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI using pure Python"""
        try:
            if len(prices) < period + 1:
                return 50.0
            
            # Convert to list for easier handling
            price_list = list(prices)
            
            # Calculate price changes
            deltas = []
            for i in range(1, len(price_list)):
                deltas.append(price_list[i] - price_list[i-1])
            
            if len(deltas) < period:
                return 50.0
            
            # Separate gains and losses
            gains = [max(delta, 0) for delta in deltas]
            losses = [abs(min(delta, 0)) for delta in deltas]
            
            # Calculate average gains and losses
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return round(rsi, 2)
        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            return 50.0
    
    def calculate_sma(self, prices, period=20):
        """Calculate Simple Moving Average"""
        try:
            price_list = list(prices)
            if len(price_list) < period:
                return sum(price_list) / len(price_list)
            
            recent_prices = price_list[-period:]
            return sum(recent_prices) / period
        except Exception as e:
            logger.error(f"SMA calculation error: {e}")
            return prices[-1] if len(prices) > 0 else 0.0
    
    def analyze_stock(self, symbol):
        """Analyze single stock for signals"""
        try:
            data = self.fetch_stock_data(symbol)
            if data is None or data.empty or len(data) < 14:
                return None
            
            # Extract price data
            closes = list(data['Close'])
            highs = list(data['High'])
            lows = list(data['Low'])
            volumes = list(data['Volume'])
            
            current_price = closes[-1]
            high_52w = max(highs)
            low_52w = min(lows)
            
            # Technical indicators
            rsi = self.calculate_rsi(closes)
            sma_20 = self.calculate_sma(closes, 20)
            
            # Volume analysis
            avg_volume = sum(volumes[-10:]) / 10 if len(volumes) >= 10 else sum(volumes) / len(volumes)
            current_volume = volumes[-1]
            
            signals = []
            
            # RSI-based signals
            if rsi < 30:
                signals.append({
                    'symbol': symbol,
                    'signal_type': 'BUY',
                    'strength': 'STRONG',
                    'price': round(current_price, 2),
                    'description': f'RSI Oversold: {rsi}',
                    'timestamp': datetime.now()
                })
            elif rsi > 70:
                signals.append({
                    'symbol': symbol,
                    'signal_type': 'SELL',
                    'strength': 'STRONG',
                    'price': round(current_price, 2),
                    'description': f'RSI Overbought: {rsi}',
                    'timestamp': datetime.now()
                })
            
            # Price vs Moving Average
            price_vs_sma = (current_price / sma_20 - 1) * 100
            if price_vs_sma > 2 and rsi < 60:
                signals.append({
                    'symbol': symbol,
                    'signal_type': 'BUY',
                    'strength': 'MEDIUM',
                    'price': round(current_price, 2),
                    'description': f'Price {price_vs_sma:.1f}% above SMA20',
                    'timestamp': datetime.now()
                })
            elif price_vs_sma < -2 and rsi > 40:
                signals.append({
                    'symbol': symbol,
                    'signal_type': 'SELL',
                    'strength': 'MEDIUM',
                    'price': round(current_price, 2),
                    'description': f'Price {abs(price_vs_sma):.1f}% below SMA20',
                    'timestamp': datetime.now()
                })
            
            # High volume analysis
            if current_volume > avg_volume * 1.5:
                if current_price > high_52w * 0.95:
                    signals.append({
                        'symbol': symbol,
                        'signal_type': 'BUY',
                        'strength': 'MEDIUM',
                        'price': round(current_price, 2),
                        'description': f'High volume breakout near 52W high',
                        'timestamp': datetime.now()
                    })
                elif current_price < low_52w * 1.05:
                    signals.append({
                        'symbol': symbol,
                        'signal_type': 'SELL',
                        'strength': 'MEDIUM',
                        'price': round(current_price, 2),
                        'description': f'High volume breakdown near 52W low',
                        'timestamp': datetime.now()
                    })
            
            return signals if signals else None
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def save_signals_to_db(self, signals):
        """Save signals to database"""
        if not signals:
            return
            
        try:
            conn = sqlite3.connect('nifty_analysis.db', check_same_thread=False)
            cursor = conn.cursor()
            
            for signal in signals:
                cursor.execute('''
                    INSERT INTO analysis_results (symbol, signal_type, strength, price, timestamp, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (signal['symbol'], signal['signal_type'], signal['strength'], 
                      signal['price'], signal['timestamp'], signal['description']))
            
            conn.commit()
            conn.close()
            logger.info(f"Saved {len(signals)} signals to database")
        except Exception as e:
            logger.error(f"Database save error: {e}")
    
    def send_telegram_message(self, message):
        """Send message to Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram not configured - skipping notification")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=30)
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def format_signals_message(self, all_signals):
        """Format signals for Telegram"""
        if not all_signals:
            return "🔍 <b>Nifty 50 Analysis</b>\n\nNo significant signals detected at this time."
        
        message = "🚀 <b>Nifty 50 Technical Signals</b>\n\n"
        
        buy_signals = [s for s in all_signals if s['signal_type'] == 'BUY']
        sell_signals = [s for s in all_signals if s['signal_type'] == 'SELL']
        
        if buy_signals:
            message += "📈 <b>BUY SIGNALS:</b>\n"
            for signal in buy_signals[:5]:  # Limit to 5
                symbol_clean = signal['symbol'].replace(".NS", "")
                message += f"• <b>{symbol_clean}</b> - ₹{signal['price']:.2f}\n"
                message += f"  📝 {signal['description']} ({signal['strength']})\n\n"
        
        if sell_signals:
            message += "📉 <b>SELL SIGNALS:</b>\n"
            for signal in sell_signals[:5]:  # Limit to 5
                symbol_clean = signal['symbol'].replace(".NS", "")
                message += f"• <b>{symbol_clean}</b> - ₹{signal['price']:.2f}\n"
                message += f"  📝 {signal['description']} ({signal['strength']})\n\n"
        
        message += f"⏰ <i>Updated: {datetime.now().strftime('%d/%m/%Y %H:%M IST')}</i>\n"
        message += f"📊 <i>Total: {len(buy_signals)} BUY, {len(sell_signals)} SELL</i>"
        
        return message
    
    def analyze_nifty_50(self):
        """Main analysis function"""
        logger.info("Starting Nifty 50 analysis...")
        all_signals = []
        processed = 0
        
        for symbol in self.nifty_symbols:
            try:
                signals = self.analyze_stock(symbol)
                if signals:
                    all_signals.extend(signals)
                
                processed += 1
                time.sleep(2)  # Rate limiting
                
                if processed % 5 == 0:
                    logger.info(f"Processed {processed}/{len(self.nifty_symbols)} stocks")
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
        
        logger.info(f"Analysis complete. Found {len(all_signals)} signals from {processed} stocks.")
        
        if all_signals:
            self.save_signals_to_db(all_signals)
            message = self.format_signals_message(all_signals)
            self.send_telegram_message(message)
        else:
            logger.info("No signals generated this cycle")
        
        return all_signals

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
            WHERE DATE(timestamp) >= DATE('now', '-1 days')
            ORDER BY timestamp DESC
            LIMIT 100
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
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'telegram_configured': bool(analyzer.telegram_token and analyzer.telegram_chat_id),
        'version': '2.0'
    })

@app.route('/api/stats')
def get_stats():
    """Get analysis statistics"""
    try:
        conn = sqlite3.connect('nifty_analysis.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM analysis_results WHERE DATE(timestamp) = DATE('now')")
        today_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM analysis_results WHERE signal_type = 'BUY' AND DATE(timestamp) = DATE('now')")
        buy_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM analysis_results WHERE signal_type = 'SELL' AND DATE(timestamp) = DATE('now')")
        sell_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'today_total': today_count,
            'today_buy': buy_count,
            'today_sell': sell_count
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'today_total': 0, 'today_buy': 0, 'today_sell': 0})

def run_analysis_loop():
    """Run analysis in background"""
    logger.info("Starting background analysis loop...")
    
    while True:
        try:
            # Run analysis every 15 minutes
            analyzer.analyze_nifty_50()
            
            # Sleep for 15 minutes
            time.sleep(900)
            
        except Exception as e:
            logger.error(f"Analysis loop error: {e}")
            time.sleep(300)  # Wait 5 minutes on error

def main():
    """Main function"""
    logger.info("Starting Simple Nifty 50 Technical Analysis App...")
    
    # Start background analysis
    analysis_thread = threading.Thread(target=run_analysis_loop, daemon=True)
    analysis_thread.start()
    
    # Run initial analysis
    try:
        logger.info("Running initial analysis...")
        analyzer.analyze_nifty_50()
    except Exception as e:
        logger.error(f"Initial analysis error: {e}")
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

if __name__ == "__main__":
    main()
