import os
import asyncio
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import sqlite3
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set. Get token from @BotFather")
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup command handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("signals", self.signals_command))
        self.application.add_handler(CommandHandler("today", self.today_signals_command))
        self.application.add_handler(CommandHandler("buy", self.buy_signals_command))
        self.application.add_handler(CommandHandler("sell", self.sell_signals_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🚀 <b>Welcome to Nifty 50 Technical Analysis Bot!</b>

This bot provides real-time technical analysis and trading signals for Nifty 50 stocks.

<b>Available Commands:</b>
/help - Show all commands
/signals - Get latest signals
/today - Today's signals summary
/buy - Show only buy signals
/sell - Show only sell signals
/status - Bot status

📈 <i>Happy Trading!</i>
        """
        await update.message.reply_text(welcome_message, parse_mode='HTML')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
📋 <b>Bot Commands:</b>

🔍 <b>/signals</b> - Get latest technical signals
📅 <b>/today</b> - Today's signals summary
📈 <b>/buy</b> - Show only buy signals
📉 <b>/sell</b> - Show only sell signals
⚡ <b>/status</b> - Check bot status

<b>Signal Strength:</b>
🟢 <b>STRONG</b> - High confidence signals
🟡 <b>MEDIUM</b> - Moderate confidence signals
🔵 <b>WEAK</b> - Low confidence signals

<b>Technical Indicators Used:</b>
• RSI (Relative Strength Index)
• MACD (Moving Average Convergence Divergence)
• Bollinger Bands
• Moving Averages (SMA/EMA)
• Volume Analysis
• Support & Resistance Levels

⚠️ <i>Disclaimer: These are technical analysis signals only. Please do your own research before trading.</i>
        """
        await update.message.reply_text(help_message, parse_mode='HTML')
    
    def get_signals_from_db(self, signal_type=None, limit=10):
        """Get signals from database"""
        conn = sqlite3.connect('nifty_analysis.db')
        cursor = conn.cursor()
        
        query = '''
            SELECT symbol, signal_type, strength, price, timestamp, description
            FROM analysis_results
            WHERE DATE(timestamp) = DATE('now')
        '''
        
        if signal_type:
            query += f" AND signal_type = '{signal_type}'"
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def format_signals_for_telegram(self, signals, title="Latest Signals"):
        """Format signals for Telegram message"""
        if not signals:
            return f"🔍 <b>{title}</b>\n\nNo signals found for today."
        
        message = f"📊 <b>{title}</b>\n\n"
        
        for signal in signals:
            symbol = signal[0].replace('.NS', '')
            signal_type = signal[1]
            strength = signal[2]
            price = signal[3]
            timestamp = signal[4]
            description = signal[5]
            
            # Format timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M')
            
            # Signal emoji
            signal_emoji = "📈" if signal_type == "BUY" else "📉"
            
            # Strength emoji
            strength_emoji = {"STRONG": "🟢", "MEDIUM": "🟡", "WEAK": "🔵"}.get(strength, "⚪")
            
            message += f"{signal_emoji} <b>{symbol}</b> - ₹{price:.2f}\n"
            message += f"{strength_emoji} <b>{signal_type}</b> ({strength})\n"
            message += f"📝 {description}\n"
            message += f"⏰ {time_str}\n\n"
        
        message += f"🕐 <i>Last updated: {datetime.now().strftime('%H:%M IST')}</i>"
        return message
    
    async def signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signals command"""
        signals = self.get_signals_from_db(limit=15)
        message = self.format_signals_for_telegram(signals, "Latest Technical Signals")
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def today_signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /today command"""
        all_signals = self.get_signals_from_db(limit=50)
        
        buy_count = len([s for s in all_signals if s[1] == 'BUY'])
        sell_count = len([s for s in all_signals if s[1] == 'SELL'])
        
        summary_message = f"""
📅 <b>Today's Signal Summary</b>

📈 <b>Buy Signals:</b> {buy_count}
📉 <b>Sell Signals:</b> {sell_count}
📊 <b>Total Signals:</b> {len(all_signals)}

<b>Recent Signals:</b>
        """
        
        recent_signals = all_signals[:10]
        for signal in recent_signals:
            symbol = signal[0].replace('.NS', '')
            signal_type = signal[1]
            strength = signal[2]
            price = signal[3]
            
            signal_emoji = "📈" if signal_type == "BUY" else "📉"
            strength_emoji = {"STRONG": "🟢", "MEDIUM": "🟡", "WEAK": "🔵"}.get(strength, "⚪")
            
            summary_message += f"\n{signal_emoji} {symbol} - {signal_type} {strength_emoji}"
        
        summary_message += f"\n\n⏰ <i>Updated: {datetime.now().strftime('%d/%m/%Y %H:%M IST')}</i>"
        
        await update.message.reply_text(summary_message, parse_mode='HTML')
    
    async def buy_signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /buy command"""
        buy_signals = self.get_signals_from_db(signal_type='BUY', limit=15)
        message = self.format_signals_for_telegram(buy_signals, "📈 Buy Signals")
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def sell_signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sell command"""
        sell_signals = self.get_signals_from_db(signal_type='SELL', limit=15)
        message = self.format_signals_for_telegram(sell_signals, "📉 Sell Signals")
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            # Check database
            conn = sqlite3.connect('nifty_analysis.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM analysis_results WHERE DATE(timestamp) = DATE('now')")
            today_signals = cursor.fetchone()[0]
            
            cursor.execute("SELECT timestamp FROM analysis_results ORDER BY timestamp DESC LIMIT 1")
            last_update = cursor.fetchone()
            conn.close()
            
            last_update_str = "Never"
            if last_update:
                dt = datetime.fromisoformat(last_update[0].replace('Z', '+00:00'))
                last_update_str = dt.strftime('%d/%m/%Y %H:%M IST')
            
            status_message = f"""
⚡ <b>Bot Status</b>

🟢 <b>Status:</b> Online
📊 <b>Today's Signals:</b> {today_signals}
🕐 <b>Last Update:</b> {last_update_str}
🔄 <b>Analysis Frequency:</b> Every 15 minutes
📈 <b>Monitoring:</b> Nifty 50 stocks

<b>System Info:</b>
• Database: ✅ Connected
• Telegram Bot: ✅ Active
• Market Hours: 9:15 AM - 3:30 PM IST

Use /signals to get latest analysis!
            """
            
            await update.message.reply_text(status_message, parse_mode='HTML')
            
        except Exception as e:
            error_message = f"❌ <b>Error checking status:</b>\n{str(e)}"
            await update.message.reply_text(error_message, parse_mode='HTML')
    
    def run(self):
        """Run the bot"""
        logger.info("Starting Telegram bot...")
        self.application.run_polling()

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
