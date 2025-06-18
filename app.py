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
        
        # Start background bot if Telegram configured
        if self.telegram_token and self.telegram_chat_id:
            threading.Thread(target=self.setup_telegram_bot, daemon=True).start()
        
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
    
    def setup_telegram_bot(self):
        """Setup Telegram bot with simple webhook check"""
        try:
            webhook_url = f"https://api.telegram.org/bot{self.telegram_token}/getMe"
            response = requests.get(webhook_url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                logger.info(f"Telegram bot connected: {bot_info.get('result', {}).get('username', 'Unknown')}")
                
                self.send_telegram_message("🚀 <b>Enhanced Nifty Bot Started!</b>\n\n✅ Ready for trading signals\n\n<i>Commands: /start, /signals</i>")
                
                self.start_command_monitoring()
            else:
                logger.error("Failed to connect to Telegram bot")
                
        except Exception as e:
            logger.error(f"Telegram setup error: {e}")
    
    def start_command_monitoring(self):
        """Monitor for commands using simple polling"""
        try:
            last_update_id = 0
            
            while True:
                try:
                    url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates"
                    params = {'offset': last_update_id + 1, 'timeout': 10}
                    
                    response = requests.get(url, params=params, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        for update in data.get('result', []):
                            last_update_id = update['update_id']
                            
                            if 'message' in update:
                                self.handle_telegram_message(update['message'])
                    
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Command monitoring error: {e}")
                    time.sleep(10)
                    
        except Exception as e:
            logger.error(f"Command monitoring setup error: {e}")
    
    def handle_telegram_message(self, message):
        """Handle incoming Telegram messages"""
        try:
            text = message.get('text', '').strip()
            chat_id = message.get('chat', {}).get('id')
            
            if not text or not chat_id:
                return
            
            text_lower = text.lower()
            
            if text.startswith('/start') or text_lower == 'start':
                response = """🚀 <b>Nifty 50 Trading Bot!</b>

📊 <b>Features:</b>
• Real-time technical analysis
• RSI, SMA indicators
• Automated signals

<b>Commands:</b>
• /signals - Latest analysis
• /analyze - Run analysis

<i>Try: "/signals"</i>"""
                
                self.send_message_to_chat(chat_id, response)
                
            elif text.startswith('/signals') or 'signals' in text_lower:
                signals = self.get_latest_signals_from_db()
                if signals:
                    message_text = self.format_signals_message(signals)
                else:
                    message_text = "🔍 <b>Running analysis...</b>\n\nPlease wait."
                    threading.Thread(target=self.analyze_nifty_50, daemon=True).start()
                
                self.send_message_to_chat(chat_id, message_text)
                
            elif text.startswith('/analyze') or 'analyze' in text_lower:
                self.send_message_to_chat(chat_id, "🔍 <b>Starting analysis...</b>")
                threading.Thread(target=self.run_immediate_analysis, args=(chat_id,), daemon=True).start()
                
            else:
                unknown_msg = """🤖 <b>Try:</b>

• /signals - Latest analysis  
• /analyze - Run analysis

<i>Example: "/signals"</i>"""
                self.send_message_to_chat(chat_id, unknown_msg)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def run_immediate_analysis(self, chat_id):
        """Run immediate analysis and send results"""
        try:
            signals = self.analyze_nifty_50()
            
            if signals:
                message = "✅ <b>Analysis Complete!</b>\n\n" + self.format_signals_message(signals)
            else:
                message = "✅ <b>Analysis Complete!</b>\n\n🔍 No strong signals detected."
            
            self.send_message_to_chat(chat_id, message)
            
        except Exception as e:
            logger.error(f"Error in immediate analysis: {e}")
    
    def send_message_to_chat(self, chat_id, message):
        """Send message to specific chat"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=30)
            if response.status_code == 200:
                logger.info(f"Message sent to chat {chat_id}")
            else:
                logger.error(f"Failed to send message: {response.text}")
        except Exception as e:
            logger.error(f"Error sending message to chat: {e}")
    
    def get_latest_signals_from_db(self):
        """Get latest signals from database"""
        try:
            conn = sqlite3.connect('nifty_analysis.db', check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT symbol, signal_type, strength, price, timestamp, description
                FROM analysis_results
                WHERE DATE(timestamp) >= DATE('now', '-1 days')
                ORDER BY timestamp DESC
                LIMIT 20
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            signals = []
            for row in results:
                signals.append({
                    'symbol': row[0],
                    'signal_type': row[1],
                    'strength': row[2],
                    'price': row[3],
                    'timestamp': row[4],
                    'description': row[5]
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting signals from DB: {e}")
            return []
        
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
            
            price_list = list(prices)
            
            deltas = []
            for i in range(1, len(price_list)):
                deltas.append(price_list[i] - price_list[i-1])
            
            if len(deltas) < period:
                return 50.0
            
            gains = [max(delta, 0) for delta in deltas]
            losses = [abs(min(delta, 0)) for delta in deltas]
            
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
            
            closes = list(data['Close'])
            current_price = closes[-1]
            
            rsi = self.calculate_rsi(closes)
            sma_20 = self.calculate_sma(closes, 20)
            
            signals = []
            
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
            return "🔍 <b>Analysis Complete</b>\n\nNo significant signals detected at this time."
        
        message = "🚀 <b>Nifty 50 Analysis</b>\n\n"
        
        buy_signals = [s for s in all_signals if s['signal_type'] == 'BUY']
        sell_signals = [s for s in all_signals if s['signal_type'] == 'SELL']
        
        if buy_signals:
            message += "📈 <b>BUY SIGNALS:</b>\n"
            for signal in buy_signals[:3]:
                symbol_clean = signal['symbol'].replace(".NS", "")
                message += f"• <b>{symbol_clean}</b> - ₹{signal['price']:.2f}\n"
                message += f"  📝 {signal['description']} ({signal['strength']})\n\n"
        
        if sell_signals:
            message += "📉 <b>SELL SIGNALS:</b>\n"
            for signal in sell_signals[:3]:
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
                time.sleep(2)
                
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
        signals = analyzer.get_latest_signals_from_db()
        
        formatted_signals = []
        for signal in signals:
            formatted_signals.append({
                'symbol': signal['symbol'].replace('.NS', ''),
                'signal_type': signal['signal_type'],
                'strength': signal['strength'],
                'price': signal['price'],
                'timestamp': signal['timestamp'],
                'description': signal['description']
            })
        
        return jsonify(formatted_signals)
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
        'version': '3.3 - Clean Fixed Version'
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
            analyzer.analyze_nifty_50()
            time.sleep(900)
            
        except Exception as e:
            logger.error(f"Analysis loop error: {e}")
            time.sleep(300)

def main():
    """Main function"""
    logger.info("Starting Enhanced Nifty 50 Bot v3.3...")
    
    analysis_thread = threading.Thread(target=run_analysis_loop, daemon=True)
    analysis_thread.start()
    
    try:
        logger.info("Running initial analysis...")
        analyzer.analyze_nifty_50()
    except Exception as e:
        logger.error(f"Initial analysis error: {e}")
    
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

if __name__ == "__main__":
    main()
