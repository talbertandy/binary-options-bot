import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import BOT_TOKEN, ADMIN_USER_ID, SUBSCRIPTION_PLANS, LOG_LEVEL, LOG_FILE
from database import Database
from signal_generator import SignalGenerator

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BinaryOptionsBot:
    def __init__(self):
        self.db = Database()
        self.signal_generator = SignalGenerator()
        self.application = None
        self.processing_users = set()  # Prevent duplicate processing
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id
        
        # Prevent duplicate processing
        if user_id in self.processing_users:
            return
        self.processing_users.add(user_id)
        
        try:
            # Add user to database
            self.db.add_user(
                user_id=user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            is_admin = user_id == ADMIN_USER_ID
            
            if is_admin:
                await self.show_admin_menu(update.message.reply_text)
            else:
                await self.show_user_menu(update.message.reply_text)
                
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")
        finally:
            self.processing_users.discard(user_id)

    async def show_admin_menu(self, reply_function):
        """Show admin menu"""
        keyboard = [
            [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton("✅ Подтвердить ID", callback_data="admin_confirm")],
            [InlineKeyboardButton("🚫 Заблокировать", callback_data="admin_block")],
            [InlineKeyboardButton("📢 Рассылка сигнала", callback_data="admin_signal")],
            [InlineKeyboardButton("✉️ Сообщение всем", callback_data="admin_message")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await reply_function(
            "👋 <b>Админ-панель</b>\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

    async def show_user_menu(self, reply_function):
        """Show user menu"""
        keyboard = [
            [InlineKeyboardButton("🔗 Зарегистрироваться", callback_data="register")],
            [InlineKeyboardButton("🆔 Отправить ID", callback_data="send_id")],
            [InlineKeyboardButton("📈 Получить сигнал", callback_data="get_signal")],
            [InlineKeyboardButton("🤝 Поддержка", url="https://t.me/razgondepoz1ta")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await reply_function(
            "👋 <b>Добро пожаловать!</b>\n\nДля получения сигналов:\n1. Зарегистрируйтесь\n2. Отправьте ID\n3. Дождитесь подтверждения\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        user_id = query.from_user.id
        
        # Prevent duplicate processing
        if user_id in self.processing_users:
            await query.answer("⏳ Обрабатывается...")
            return
        self.processing_users.add(user_id)
        
        try:
            await query.answer()
            data = query.data
            
            is_admin = user_id == ADMIN_USER_ID
            
            if is_admin:
                await self.handle_admin_callback(query, data)
            else:
                await self.handle_user_callback(query, data)
                
        except Exception as e:
            logger.error(f"Error in button_callback: {e}")
            await query.edit_message_text("❌ Ошибка. Попробуйте еще раз.")
        finally:
            self.processing_users.discard(user_id)

    async def handle_admin_callback(self, query, data):
        """Handle admin callbacks"""
        if data == "admin_users":
            await self.show_users_list(query)
        elif data == "admin_confirm":
            await self.show_pending_users(query)
        elif data == "admin_block":
            await self.show_users_for_block(query)
        elif data == "admin_signal":
            await self.show_signal_form(query)
        elif data == "admin_message":
            await self.show_message_form(query)
        elif data.startswith("confirm_"):
            user_id = int(data.split("_")[1])
            await self.confirm_user(query, user_id)
        elif data.startswith("block_"):
            user_id = int(data.split("_")[1])
            await self.block_user(query, user_id)
        elif data == "back_admin":
            await self.show_admin_menu(query.edit_message_text)

    async def handle_user_callback(self, query, data):
        """Handle user callbacks"""
        if data == "register":
            await query.edit_message_text(
                "🔗 <b>Регистрация</b>\n\nПерейдите по ссылке:\nhttps://bit.ly/4jb8a4k\n\nПосле регистрации отправьте ID.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_user")]]),
                parse_mode=ParseMode.HTML
            )
        elif data == "send_id":
            await query.edit_message_text(
                "🆔 <b>Отправка ID</b>\n\nНапишите ваш ID после регистрации:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_user")]]),
                parse_mode=ParseMode.HTML
            )
        elif data == "get_signal":
            await self.send_signal_to_user(query)
        elif data == "back_user":
            await self.show_user_menu(query.edit_message_text)

    async def show_users_list(self, query):
        """Show users list for admin"""
        users = self.db.get_all_users_detailed()
        
        if not users:
            text = "👥 Пользователей нет"
        else:
            text = "👥 <b>Список пользователей:</b>\n\n"
            for user in users[:10]:
                status = user.get('id_status', 'pending')
                emoji = "✅" if status == 'confirmed' else "⏳" if status == 'pending' else "❌"
                text += f"{emoji} ID: {user['user_id']} | {user.get('first_name', 'Неизвестно')} | {status}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]],
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def show_pending_users(self, query):
        """Show pending users for confirmation"""
        users = self.db.get_pending_users()
        
        if not users:
            text = "⏳ Нет пользователей ожидающих подтверждения"
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]],
        else:
            text = "⏳ <b>Пользователи ожидающие подтверждения:</b>\n\n"
            keyboard = []
            
            for user in users:
                text += f"👤 ID: {user['user_id']} | {user.get('first_name', 'Неизвестно')}\n"
                keyboard.append([InlineKeyboardButton(f"✅ Подтвердить {user['user_id']}", callback_data=f"confirm_{user['user_id']}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_admin")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def show_users_for_block(self, query):
        """Show users for blocking"""
        users = self.db.get_all_users_detailed()
        
        if not users:
            text = "👥 Нет пользователей для блокировки"
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]],
        else:
            text = "🚫 <b>Выберите пользователя для блокировки:</b>\n\n"
            keyboard = []
            
            for user in users:
                text += f"👤 ID: {user['user_id']} | {user.get('first_name', 'Неизвестно')}\n"
                keyboard.append([InlineKeyboardButton(f"🚫 Блок {user['user_id']}", callback_data=f"block_{user['user_id']}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_admin")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def confirm_user(self, query, user_id):
        """Confirm user access"""
        self.db.confirm_user_id(user_id)
        
        # Notify user
        try:
            await self.application.bot.send_message(
                user_id,
                "✅ <b>Доступ подтвержден!</b>\n\nТеперь вы будете получать сигналы автоматически.",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        
        await query.edit_message_text(
            f"✅ Пользователь {user_id} подтвержден!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_confirm")]])
        )

    async def block_user(self, query, user_id):
        """Block user"""
        self.db.block_user(user_id)
        
        # Notify user
        try:
            await self.application.bot.send_message(
                user_id,
                "🚫 <b>Доступ заблокирован</b>",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        
        await query.edit_message_text(
            f"🚫 Пользователь {user_id} заблокирован!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_block")]])
        )

    async def show_signal_form(self, query):
        """Show signal broadcast form"""
        await query.edit_message_text(
            "📢 <b>Рассылка сигнала</b>\n\nНапишите сигнал в формате:\nАктив ВХОД Время\n\nНапример:\nEUR/USD ВВЕРХ 2мин",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]]),
            parse_mode=ParseMode.HTML
        )

    async def show_message_form(self, query):
        """Show message broadcast form"""
        await query.edit_message_text(
            "✉️ <b>Сообщение всем</b>\n\nНапишите сообщение для рассылки:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]]),
            parse_mode=ParseMode.HTML
        )

    async def send_signal_to_user(self, query):
        """Send signal to user"""
        user = self.db.get_user(query.from_user.id)
        
        if not user or user.get('id_status') != 'confirmed':
            await query.edit_message_text(
                "⛔️ <b>Доступ закрыт</b>\n\nДождитесь подтверждения от администратора.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_user")]]),
                parse_mode=ParseMode.HTML
            )
            return
        
        # Generate signal
        signal = self.signal_generator.generate_signal()
        if not signal:
            await query.edit_message_text(
                "😔 Сейчас нет сигналов",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_user")]])
            )
            return
        
        # Format signal
        text = f"""
📢 <b>СИГНАЛ</b>

📍 Актив: {signal['asset']}
📈 ВХОД: {'ВВЕРХ' if signal['signal_type']=='CALL' else 'ВНИЗ'}
⏱️ Время: {signal['expiry_time']}
💰 Вход: {signal['entry_price']}
🎯 Цель: {signal['target_price']}
📊 Точность: {signal['accuracy']}%

⏰ {signal['timestamp'].strftime('%H:%M:%S')}
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Еще сигнал", callback_data="get_signal")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_user")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user = update.effective_user
        user_id = user.id
        text = update.message.text.strip()
        
        # Prevent duplicate processing
        if user_id in self.processing_users:
            return
        self.processing_users.add(user_id)
        
        try:
            if user_id == ADMIN_USER_ID:
                await self.handle_admin_message(update, text)
            else:
                await self.handle_user_message(update, text)
        except Exception as e:
            logger.error(f"Error handling message: {e}")
        finally:
            self.processing_users.discard(user_id)

    async def handle_admin_message(self, update: Update, text: str):
        """Handle admin messages"""
        # Check if it's a signal
        if any(keyword in text.upper() for keyword in ['EUR/USD', 'GBP/USD', 'USD/JPY', 'ВВЕРХ', 'ВНИЗ']):
            await self.broadcast_signal(text)
            await update.message.reply_text("✅ Сигнал разослан!")
        else:
            await self.broadcast_message(text)
            await update.message.reply_text("✅ Сообщение разослано!")

    async def handle_user_message(self, update: Update, text: str):
        """Handle user messages"""
        if not text.isdigit():
            await update.message.reply_text("❗️ ID должен содержать только цифры")
            return
        
        # Check if ID already exists
        existing = self.db.get_user_by_platform_id(text)
        if existing and existing.get('user_id') != update.effective_user.id:
            await update.message.reply_text("⛔️ Этот ID уже используется")
            return
        
        # Save ID
        self.db.set_platform_id(update.effective_user.id, text)
        await update.message.reply_text("✅ ID сохранен! Ожидайте подтверждения.")
        
        # Notify admin
        await self.notify_admin_new_id(update.effective_user, text)

    async def notify_admin_new_id(self, user, platform_id):
        """Notify admin about new ID"""
        try:
            text = f"""
🆔 <b>Новый ID!</b>

👤 {user.first_name or user.username}
🆔 {user.id}
📱 {platform_id}
⏰ {datetime.now().strftime('%H:%M')}
            """
            
            keyboard = [
                [InlineKeyboardButton(f"✅ Подтвердить {user.id}", callback_data=f"confirm_{user.id}")],
                [InlineKeyboardButton(f"🚫 Блок {user.id}", callback_data=f"block_{user.id}")]
            ]
            
            await self.application.bot.send_message(
                ADMIN_USER_ID,
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")

    async def broadcast_signal(self, signal_text: str):
        """Broadcast signal to confirmed users"""
        users = self.db.get_all_users_detailed()
        confirmed_users = [user for user in users if user.get('id_status') == 'confirmed']
        
        text = f"""
🚨 <b>СИГНАЛ!</b>

{signal_text}

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        for user in confirmed_users:
            try:
                await self.application.bot.send_message(
                    user['user_id'],
                    text,
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(0.05)  # Small delay
            except:
                continue

    async def broadcast_message(self, message_text: str):
        """Broadcast message to all users"""
        users = self.db.get_all_users_detailed()
        
        text = f"""
📢 <b>Сообщение от администратора:</b>

{message_text}

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        for user in users:
            try:
                await self.application.bot.send_message(
                    user['user_id'],
                    text,
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(0.05)  # Small delay
            except:
                continue

    async def auto_broadcast_signals(self):
        """Auto broadcast signals every 15 minutes"""
        while True:
            try:
                await asyncio.sleep(15 * 60)  # 15 minutes
                
                signal = self.signal_generator.generate_signal()
                if signal:
                    await self.broadcast_signal(f"📍 {signal['asset']}\n📈 {'ВВЕРХ' if signal['signal_type']=='CALL' else 'ВНИЗ'}\n⏱️ {signal['expiry_time']}")
                    
            except Exception as e:
                logger.error(f"Error in auto broadcast: {e}")
                await asyncio.sleep(60)

    def setup_handlers(self):
        """Setup bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def run(self):
        """Run the bot"""
        try:
            if not BOT_TOKEN:
                logger.error("BOT_TOKEN not found")
                return
            
            self.application = Application.builder().token(BOT_TOKEN).build()
            self.setup_handlers()
            
            logger.info("Starting bot...")
            
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # Start auto broadcast
            asyncio.create_task(self.auto_broadcast_signals())
            
            logger.info("Bot started successfully!")
            
            # Keep running
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Critical error: {e}")
        finally:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            except:
                pass

def run_http_stub():
    try:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Bot is running!")
            
            def log_message(self, format, *args):
                pass
        
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("", port), Handler)
        server.serve_forever()
    except Exception as e:
        logger.error(f"HTTP server error: {e}")

# Start HTTP server
threading.Thread(target=run_http_stub, daemon=True).start()

async def main():
    """Main function"""
    try:
        bot = BinaryOptionsBot()
        await bot.run()
    except Exception as e:
        logger.error(f"Main error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 