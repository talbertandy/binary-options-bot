import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import random
from datetime import datetime

# Подробное логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_USER_ID', '0'))

logger.info(f"BOT_TOKEN: {'SET' if BOT_TOKEN else 'NOT SET'}")
logger.info(f"ADMIN_ID: {ADMIN_ID}")

# Простая база данных в памяти
users = {}
pending_ids = {}

class SimpleBot:
    def __init__(self):
        self.app = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        logger.info(f"START command from user {update.effective_user.id}")
        
        user = update.effective_user
        user_id = user.id
        
        # Добавляем пользователя
        if user_id not in users:
            users[user_id] = {
                'name': user.first_name or user.username,
                'status': 'new',
                'platform_id': None
            }
            logger.info(f"New user added: {user_id}")
        
        # Показываем меню
        if user_id == ADMIN_ID:
            logger.info("Showing admin menu")
            await self.show_admin_menu(update.message.reply_text)
        else:
            logger.info("Showing user menu")
            await self.show_user_menu(update.message.reply_text)
    
    async def show_user_menu(self, reply_func):
        """Показать меню пользователя"""
        logger.info("Creating user menu")
        keyboard = [
            [InlineKeyboardButton("🔗 Регистрация", callback_data="register")],
            [InlineKeyboardButton("🆔 Отправить ID", callback_data="send_id")],
            [InlineKeyboardButton("📈 Сигнал", callback_data="signal")],
            [InlineKeyboardButton("🤝 Поддержка", url="https://t.me/razgondepoz1ta")]
        ]
        
        try:
            await reply_func(
                "👋 <b>Добро пожаловать!</b>\n\n1. Зарегистрируйтесь\n2. Отправьте ID\n3. Получите сигналы",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            logger.info("User menu sent successfully")
        except Exception as e:
            logger.error(f"Error sending user menu: {e}")
    
    async def show_admin_menu(self, reply_func):
        """Показать админ меню"""
        logger.info("Creating admin menu")
        keyboard = [
            [InlineKeyboardButton("👥 Пользователи", callback_data="users")],
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
            [InlineKeyboardButton("📢 Сигнал всем", callback_data="broadcast")]
        ]
        
        try:
            await reply_func(
                "👋 <b>Админ-панель</b>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            logger.info("Admin menu sent successfully")
        except Exception as e:
            logger.error(f"Error sending admin menu: {e}")
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопок"""
        logger.info(f"Button callback: {update.callback_query.data} from user {update.callback_query.from_user.id}")
        
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        try:
            if user_id == ADMIN_ID:
                await self.handle_admin_callback(query, data)
            else:
                await self.handle_user_callback(query, data)
        except Exception as e:
            logger.error(f"Error in button handler: {e}")
            await query.edit_message_text("❌ Ошибка. Попробуйте еще раз.")
    
    async def handle_user_callback(self, query, data):
        """Обработка кнопок пользователя"""
        logger.info(f"User callback: {data}")
        
        if data == "register":
            await query.edit_message_text(
                "🔗 <b>Регистрация</b>\n\nПерейдите: https://bit.ly/4jb8a4k\n\nПосле регистрации отправьте ID.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]),
                parse_mode=ParseMode.HTML
            )
        
        elif data == "send_id":
            await query.edit_message_text(
                "🆔 <b>Отправьте ваш ID</b>\n\nНапишите ID после регистрации:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]),
                parse_mode=ParseMode.HTML
            )
        
        elif data == "signal":
            user = users.get(query.from_user.id, {})
            if user.get('status') == 'confirmed':
                signal = self.generate_signal()
                await query.edit_message_text(
                    f"📈 <b>СИГНАЛ</b>\n\n{signal}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]),
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.edit_message_text(
                    "⛔️ <b>Доступ закрыт</b>\n\nДождитесь подтверждения.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]),
                    parse_mode=ParseMode.HTML
                )
        
        elif data == "back":
            await self.show_user_menu(query.edit_message_text)
    
    async def handle_admin_callback(self, query, data):
        """Обработка кнопок админа"""
        logger.info(f"Admin callback: {data}")
        
        if data == "users":
            text = "👥 <b>Пользователи:</b>\n\n"
            for uid, user in users.items():
                status = user.get('status', 'new')
                emoji = "✅" if status == 'confirmed' else "⏳" if status == 'pending' else "❌"
                text += f"{emoji} {uid}: {user.get('name', 'Неизвестно')} - {status}\n"
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]]),
                parse_mode=ParseMode.HTML
            )
        
        elif data == "confirm":
            if pending_ids:
                text = "⏳ <b>Ожидают подтверждения:</b>\n\n"
                keyboard = []
                for uid, platform_id in pending_ids.items():
                    user_name = users.get(uid, {}).get('name', 'Неизвестно')
                    text += f"👤 {uid}: {user_name} - {platform_id}\n"
                    keyboard.append([InlineKeyboardButton(f"✅ {uid}", callback_data=f"confirm_{uid}")])
                
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_admin")])
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.edit_message_text(
                    "⏳ Нет пользователей для подтверждения",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]])
                )
        
        elif data == "broadcast":
            await query.edit_message_text(
                "📢 <b>Отправьте сигнал</b>\n\nНапишите сигнал в формате:\nАктив ВХОД Время",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]]),
                parse_mode=ParseMode.HTML
            )
        
        elif data.startswith("confirm_"):
            uid = int(data.split("_")[1])
            if uid in users:
                users[uid]['status'] = 'confirmed'
                if uid in pending_ids:
                    del pending_ids[uid]
                
                # Уведомляем пользователя
                try:
                    await self.app.bot.send_message(uid, "✅ <b>Доступ подтвержден!</b>", parse_mode=ParseMode.HTML)
                except:
                    pass
                
                await query.edit_message_text(
                    f"✅ Пользователь {uid} подтвержден!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="confirm")]])
                )
        
        elif data == "back_admin":
            await self.show_admin_menu(query.edit_message_text)
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        logger.info(f"Message from {user_id}: {text}")
        
        try:
            if user_id == ADMIN_ID:
                # Админ отправляет сигнал
                if any(word in text.upper() for word in ['EUR/USD', 'GBP/USD', 'USD/JPY', 'ВВЕРХ', 'ВНИЗ']):
                    await self.broadcast_signal(text)
                    await update.message.reply_text("✅ Сигнал разослан!")
                else:
                    await update.message.reply_text("📢 Сообщение разослано всем!")
            else:
                # Пользователь отправляет ID
                if text.isdigit():
                    if user_id not in users:
                        users[user_id] = {'name': update.effective_user.first_name, 'status': 'new'}
                    
                    users[user_id]['platform_id'] = text
                    users[user_id]['status'] = 'pending'
                    pending_ids[user_id] = text
                    
                    await update.message.reply_text("✅ ID сохранен! Ожидайте подтверждения.")
                    
                    # Уведомляем админа
                    try:
                        await self.app.bot.send_message(
                            ADMIN_ID,
                            f"🆔 <b>Новый ID!</b>\n\n👤 {update.effective_user.first_name}\n🆔 {user_id}\n📱 {text}",
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        logger.error(f"Error notifying admin: {e}")
                else:
                    await update.message.reply_text("❗️ ID должен содержать только цифры")
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            await update.message.reply_text("❌ Ошибка. Попробуйте еще раз.")
    
    def generate_signal(self):
        """Генерация простого сигнала"""
        assets = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"]
        directions = ["ВВЕРХ", "ВНИЗ"]
        times = ["1мин", "2мин", "3мин", "5мин"]
        
        asset = random.choice(assets)
        direction = random.choice(directions)
        time = random.choice(times)
        
        return f"📍 {asset}\n📈 {direction}\n⏱️ {time}\n⏰ {datetime.now().strftime('%H:%M')}"
    
    async def broadcast_signal(self, signal_text):
        """Рассылка сигнала всем подтвержденным пользователям"""
        confirmed_users = [uid for uid, user in users.items() if user.get('status') == 'confirmed']
        
        text = f"🚨 <b>СИГНАЛ!</b>\n\n{signal_text}"
        
        for uid in confirmed_users:
            try:
                await self.app.bot.send_message(uid, text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Error sending signal to {uid}: {e}")
                continue
    
    async def run(self):
        """Запуск бота"""
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN не найден!")
            return
        
        logger.info("Создаем приложение...")
        self.app = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        logger.info("Добавляем обработчики...")
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
        
        logger.info("Бот запускается...")
        
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            logger.info("Бот запущен успешно!")
            
            # Держим бота запущенным
            await self.app.updater.idle()
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")

# HTTP сервер для Cloud Run
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

def run_http_server():
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
    logger.info(f"HTTP server started on port {port}")
    server.serve_forever()

# Запускаем HTTP сервер в фоне
threading.Thread(target=run_http_server, daemon=True).start()

# Запускаем бота
if __name__ == "__main__":
    import asyncio
    logger.info("Starting bot application...")
    bot = SimpleBot()
    asyncio.run(bot.run()) 