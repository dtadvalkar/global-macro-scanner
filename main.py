import os
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Telegram Token from environment secrets
TELEGRAM_TOKEN = os.getenv("telegram_token")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Stock Screener Bot started! Use /price <symbol> to get live data.')

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('Please provide a ticker symbol. Example: /price AAPL')
        return
    
    symbol = context.args[0].upper()
    try:
        ticker = yf.Ticker(symbol)
        # yfinance info can be slow or fail, use fast_info or specific attributes if needed
        info = ticker.info
        current_price = info.get('regularMarketPrice') or info.get('currentPrice')
        
        if current_price:
            name = info.get('longName', symbol)
            change = info.get('regularMarketChangePercent', 0)
            await update.message.reply_text(f"{name} ({symbol}): ${current_price:.2f} ({change:+.2f}%)")
        else:
            await update.message.reply_text(f"Could not find price for {symbol}")
    except Exception as e:
        await update.message.reply_text(f"Error fetching data for {symbol}: {str(e)}")

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("Error: telegram_token secret not found.")
    else:
        # Create the application
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('price', price))
        
        print("Bot is starting...")
        application.run_polling()
