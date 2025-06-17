# Quick Start Script for Nifty 50 Analysis App
import os
import subprocess
import sys

def install_requirements():
    """Install required packages"""
    print("📦 Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ Requirements installed successfully!")

def create_env_file():
    """Create environment file"""
    if not os.path.exists('.env'):
        print("🔧 Creating .env file...")
        with open('.env', 'w') as f:
            f.write("TELEGRAM_BOT_TOKEN=your_bot_token_here\n")
            f.write("TELEGRAM_CHAT_ID=your_chat_id_here\n")
            f.write("PORT=5000\n")
        print("✅ .env file created! Please update with your tokens.")
        return False
    return True

def main():
    """Main setup function"""
    print("🚀 Setting up Nifty 50 Analysis App...")
    
    # Install requirements
    try:
        install_requirements()
    except Exception as e:
        print(f"❌ Error installing requirements: {e}")
        return
    
    # Create env file
    env_exists = create_env_file()
    
    if not env_exists:
        print("\n⚠️  Please update the .env file with your Telegram bot token and chat ID")
        print("   Then run: python app.py")
        return
    
    print("\n🎉 Setup complete!")
    print("🔗 Run the app: python app.py")
    print("🤖 Run telegram bot: python telegram_bot.py")
    print("📊 Dashboard: http://localhost:5000")

if __name__ == "__main__":
    main()