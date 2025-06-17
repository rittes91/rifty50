import os
import requests
import pandas as pd
import numpy as np
import time
import asyncio
from datetime import datetime, timedelta
import yfinance as yf
from telegram import Bot
from telegram.error import TelegramError
import sqlite3
import schedule
import threading
from flask import Flask, render_template, jsonify
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
import ta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TechnicalSignal:
    symbol: str
    signal_type: str
    strength: str
    price: float
    timestamp: datetime
    description: str

class NiftyAnalyzer:
    def __init__(self):
        self.nifty_symbols = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
            "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
            "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS",
            "TITAN.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS",
            "TATAMOTORS.NS", "WIPRO.NS", "ONGC.NS", "JSWSTEEL.NS", "M&M.NS",
            "TECHM.NS", "TATASTEEL.NS", "HCLTECH.NS", "DRREDDY.NS", "INDUSINDBK.NS",
            "CIPLA.NS", "COALINDIA.NS", "EICHERMOT.NS", "GRASIM.NS", "BRITANNIA.NS",
            "DIVISLAB.NS", "BAJFINANCE.NS", "APOLLOHOSP.NS", "HDFCLIFE.NS", "SBILIFE.NS",
            "BAJAJFINSV.NS", "ADANIPORTS.NS", "TATACONSUM.NS", "UPL.NS", "HEROMOTOCO.NS",
            "BPCL.NS", "HINDALCO.NS", "LTIM.NS", "ADANIENT.NS", "BAJAJ-AUTO.NS"
        ]
        
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.bot = Bot(token=self.telegram_token) if self.telegram_token else None
        
        # Initialize database
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for storing analysis data"""
        conn = sqlite3.connect('nifty_analysis.db')
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                date DATE,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                timestamp DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def fetch_stock_data(self, symbol: str, period: str = "1mo") -> Optional[pd.DataFrame]:
        """Fetch stock data using yfinance"""
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period=period)
            if data.empty:
                logger.warning(f"No data found for {symbol}")
                return None
            return data
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> Dict:
        """Calculate various technical indicators"""
        try:
            indicators = {}
            
            # RSI
            indicators['rsi'] = ta.momentum.RSIIndicator(data['Close']).rsi().iloc[-1]
            
            # MACD
            macd = ta.trend.MACD(data['Close'])
            indicators['macd'] = macd.macd().iloc[-1]
            indicators['macd_signal'] = macd.macd_signal().iloc[-1]
            indicators['macd_histogram'] = macd.macd_diff().iloc[-1]
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(data['Close'])
            indicators['bb_upper'] = bb.bollinger_hband().iloc[-1]
            indicators['bb_middle'] = bb.bollinger_mavg().iloc[-1]
            indicators['bb_lower'] = bb.bollinger_lband().iloc[-1]
            
            # Moving Averages
            indicators['sma_20'] = ta.trend.SMAIndicator(data['Close'], window=20).sma_indicator().iloc[-1]
            indicators['sma_50'] = ta.trend.SMAIndicator(data['Close'], window=50).sma_indicator().iloc[-1]
            indicators['ema_12'] = ta.trend.EMAIndicator(data['Close'], window=12).ema_indicator().iloc[-1]
            indicators['ema_26'] = ta.trend.EMAIndicator(data['Close'], window=26).ema_indicator().iloc[-1]
            
            # Volume indicators
            indicators['volume_sma'] = data['Volume'].rolling(window=20).mean().iloc[-1]
            
            # Support and Resistance
            indicators['support'] = data['Low'].rolling(window=20).min().iloc[-1]
            indicators['resistance'] = data['High'].rolling(window=20).max().iloc[-1]
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return {}
    
    def analyze_signals(self, symbol: str, data: pd.DataFrame, indicators: Dict) -> List[TechnicalSignal]:
        """Analyze technical signals"""
        signals = []
        current_price = data['Close'].iloc[-1]
        
        try:
            # RSI Signals
            if indicators.get('rsi'):
                if indicators['rsi'] < 30:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        signal_type="BUY",
                        strength="STRONG",
                        price=current_price,
                        timestamp=datetime.now(),
                        description=f"RSI Oversold: {indicators['rsi']:.2f}"
                    ))
                elif indicators['rsi'] > 70:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        signal_type="SELL",
                        strength="STRONG",
                        price=current_price,
                        timestamp=datetime.now(),
                        description=f"RSI Overbought: {indicators['rsi']:.2f}"
                    ))
            
            # MACD Signals
            if indicators.get('macd') and indicators.get('macd_signal'):
                if indicators['macd'] > indicators['macd_signal'] and indicators['macd_histogram'] > 0:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        signal_type="BUY",
                        strength="MEDIUM",
                        price=current_price,
                        timestamp=datetime.now(),
                        description="MACD Bullish Crossover"
                    ))
                elif indicators['macd'] < indicators['macd_signal'] and indicators['macd_histogram'] < 0:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        signal_type="SELL",
                        strength="MEDIUM",
                        price=current_price,
                        timestamp=datetime.now(),
                        description="MACD Bearish Crossover"
                    ))
            
            # Bollinger Bands Signals
            if indicators.get('bb_lower') and indicators.get('bb_upper'):
                if current_price <= indicators['bb_lower']:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        signal_type="BUY",
                        strength="MEDIUM",
                        price=current_price,
                        timestamp=datetime.now(),
                        description="Price at Lower Bollinger Band"
                    ))
                elif current_price >= indicators['bb_upper']:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        signal_type="SELL",
                        strength="MEDIUM",
                        price=current_price,
                        timestamp=datetime.now(),
                        description="Price at Upper Bollinger Band"
                    ))
            
            # Moving Average Crossover
            if indicators.get('sma_20') and indicators.get('sma_50'):
                if indicators['sma_20'] > indicators['sma_50'] and current_price > indicators['sma_20']:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        signal_type="BUY",
                        strength="WEAK",
                        price=current_price,
                        timestamp=datetime.now(),
                        description="Golden Cross - Bullish Trend"
                    ))
            
            return signals
            
        except Exception as e:
            logger.error(f"Error analyzing signals for {symbol}: {e}")
            return []
    
    def save_signals_to_db(self, signals: List[TechnicalSignal]):
        """Save signals to database"""
        conn = sqlite3.connect('nifty_analysis.db')
        cursor = conn.cursor()
        
        for signal in signals:
            cursor.execute('''
                INSERT INTO analysis_results (symbol, signal_type, strength, price, timestamp, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (signal.symbol, signal.signal_type, signal.strength, signal.price, 
                  signal.timestamp, signal.description))
        
        conn.commit()
        conn.close()
    
    async def send_telegram_message(self, message: str):
        """Send message to Telegram channel"""
        if not self.bot or not self.telegram_chat_id:
            logger.warning("Telegram bot not configured")
            return
            
        try:
            await self.bot.send_message(chat_id=self.telegram_chat_id, text=message, parse_mode='HTML')
            logger.info("Telegram message sent successfully")
        except TelegramError as e:
            logger.error(f"Error sending Telegram message: {e}")
    
    def format_signals_message(self, signals: List[TechnicalSignal]) -> str:
        """Format signals for Telegram message"""
        if not signals:
            return "🔍 <b>Nifty 50 Analysis</b>\n\nNo significant signals detected at this time."
        
        message = "🚀 <b>Nifty 50 Technical Signals</b>\n\n"
        
        buy_signals = [s for s in signals if s.signal_type == "BUY"]
        sell_signals = [s for s in signals if s.signal_type == "SELL"]
        
        if buy_signals:
            message += "📈 <b>BUY SIGNALS:</b>\n"
            for signal in buy_signals:
                symbol_clean = signal.symbol.replace(".NS", "")
                message += f"• <b>{symbol_clean}</b> - ₹{signal.price:.2f}\n"
                message += f"  {signal.description} ({signal.strength})\n\n"
        
        if sell_signals:
            message += "📉 <b>SELL SIGNALS:</b>\n"
            for signal in sell_signals:
                symbol_clean = signal.symbol.replace(".NS", "")
                message += f"• <b>{symbol_clean}</b> - ₹{signal.price:.2f}\n"
                message += f"  {signal.description} ({signal.strength})\n\n"
        
        message += f"⏰ <i>Updated: {datetime.now().strftime('%d/%m/%Y %H:%M IST')}</i>"
        return message
    
    def analyze_nifty_50(self):
        """Main analysis function"""
        logger.info("Starting Nifty 50 analysis...")
        all_signals = []
        
        for symbol in self.nifty_symbols:
            try:
                # Fetch data
                data = self.fetch_stock_data(symbol)
                if data is None or data.empty:
                    continue
                
                # Calculate indicators
                indicators = self.calculate_technical_indicators(data)
                if not indicators:
                    continue
                
                # Analyze signals
                signals = self.analyze_signals(symbol, data, indicators)
                all_signals.extend(signals)
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
        
        # Save signals to database
        if all_signals:
            self.save_signals_to_db(all_signals)
            
            # Send to Telegram
            message = self.format_signals_message(all_signals)
            asyncio.run(self.send_telegram_message(message))
            
        logger.info(f"Analysis complete. Found {len(all_signals)} signals.")
        return all_signals

# Flask Web Interface
app = Flask(__name__)
analyzer = NiftyAnalyzer()

@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/latest-signals')
def get_latest_signals():
    """API endpoint for latest signals"""
    conn = sqlite3.connect('nifty_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT symbol, signal_type, strength, price, timestamp, description
        FROM analysis_results
        WHERE DATE(timestamp) = DATE('now')
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

# Scheduler
def run_scheduler():
    """Run the scheduler in a separate thread"""
    schedule.every(15).minutes.do(analyzer.analyze_nifty_50)  # Analyze every 15 minutes
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def main():
    """Main function"""
    # Start scheduler in background
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Run initial analysis
    analyzer.analyze_nifty_50()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()
