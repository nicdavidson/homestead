"""
Hearth Integrations - Telegram
Telegram bot for remote access.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from core import Config, get_config
from agents import Gateway

logger = logging.getLogger("hearth.telegram")


class TelegramBot:
    """
    Telegram bot integration for Hearth.
    
    Handles:
    - Incoming messages
    - Notifications (morning newspaper, alerts)
    - Quiet hours
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.gateway = Gateway(config)
        self.token = self.config.telegram_token
        self.chat_id = self.config.telegram_chat_id
        self._running = False
    
    async def start(self):
        """Start the Telegram bot."""
        if not self.token:
            logger.error("Telegram token not configured")
            return
        
        try:
            from telegram import Update, Bot
            from telegram.ext import Application, MessageHandler, CommandHandler, filters
        except ImportError:
            logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
            return
        
        self._running = True
        
        # Create application
        app = Application.builder().token(self.token).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("status", self._cmd_status))
        app.add_handler(CommandHandler("costs", self._cmd_costs))
        app.add_handler(CommandHandler("reflect", self._cmd_reflect))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        logger.info("Starting Telegram bot...")
        
        # Run polling
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Keep running
        while self._running:
            await asyncio.sleep(1)
        
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
    
    def stop(self):
        """Stop the bot."""
        self._running = False
    
    async def _cmd_start(self, update, context):
        """Handle /start command."""
        await update.message.reply_text(
            "Hearth is running. Send me a message to chat."
        )
    
    async def _cmd_status(self, update, context):
        """Handle /status command."""
        response = self.gateway.process("status", channel="telegram")
        await update.message.reply_text(response.content)
    
    async def _cmd_costs(self, update, context):
        """Handle /costs command."""
        response = self.gateway.process("costs", channel="telegram")
        await update.message.reply_text(response.content)
    
    async def _cmd_reflect(self, update, context):
        """Handle /reflect command."""
        await update.message.reply_text("Starting reflection...")
        response = self.gateway.process("reflect", channel="telegram")
        await update.message.reply_text(response.content[:4000])  # TG limit
    
    async def _handle_message(self, update, context):
        """Handle incoming text messages."""
        message = update.message.text
        chat_id = str(update.message.chat_id)
        
        # Check if from authorized chat
        if self.chat_id and chat_id != self.chat_id:
            await update.message.reply_text("Unauthorized.")
            return
        
        logger.info(f"Message from {chat_id}: {message[:50]}...")
        
        try:
            response = self.gateway.process(
                message,
                channel="telegram",
                session_id=f"telegram-{chat_id}"
            )
            
            # Split long messages
            content = response.content
            if len(content) > 4000:
                chunks = [content[i:i+4000] for i in range(0, len(content), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(content)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(f"Error: {str(e)[:200]}")
    
    async def send_message(self, text: str, silent: bool = False):
        """Send a message to the configured chat."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram not configured, can't send message")
            return
        
        # Check quiet hours
        if silent and self.config.is_quiet_hours():
            logger.info("Quiet hours, message queued")
            return
        
        try:
            from telegram import Bot
            bot = Bot(token=self.token)
            await bot.send_message(chat_id=self.chat_id, text=text[:4000])
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    async def send_newspaper(self):
        """Send the morning newspaper."""
        response = self.gateway.process("newspaper", channel="telegram")
        await self.send_message(f"📰 Good morning!\n\n{response.content}")
    
    async def send_alert(self, message: str, urgent: bool = False):
        """Send an alert. Ignores quiet hours if urgent."""
        prefix = "🚨 " if urgent else "⚠️ "
        await self.send_message(prefix + message, silent=not urgent)


def run_telegram_bot(config: Optional[Config] = None):
    """Run the Telegram bot (blocking)."""
    bot = TelegramBot(config)
    asyncio.run(bot.start())
