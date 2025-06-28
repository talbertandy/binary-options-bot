import logging
import asyncio
import schedule
import time
from datetime import datetime, timedelta
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
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command (customized for registration flow)"""
        user = update.effective_user
        user_id = user.id
        self.db.add_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        is_admin = user_id == ADMIN_USER_ID
        if is_admin:
            welcome_message = (
                "👋 <b>Привет, Админ!</b>\n\n"
                "Ты в админ-меню. Здесь ты можешь:\n"
                "• Подтверждать/блокировать пользователей\n"
                "• Рассылать сигналы\n"
                "• Смотреть список юзеров\n"
                "• Писать от имени бота\n\n"
                "Выбери действие:")
            keyboard = [
                [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users"), InlineKeyboardButton("✅ Подтвердить ID", callback_data="admin_confirm")],
                [InlineKeyboardButton("🚫 Заблокировать", callback_data="admin_block"), InlineKeyboardButton("📢 Рассылка сигнала", callback_data="admin_signal")],
                [InlineKeyboardButton("✉️ Личное сообщение", callback_data="admin_send")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="admin_main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            welcome_message = (
                "👋 Привет, трейдер!\n\n"
                "Тут работают только те, кто реально заходит в сделки и поднимает.\n\n"
                "📊 Я даю сигналы на вход. Что делать тебе — просто следовать.\n\n"
                "Но сначала — 3 шага:\n"
                "1. Регистрируешься по ссылке\n"
                "2. Скидываешь ID\n"
                "3. Депаешь — и получаешь доступ ко всем сигналам\n\n"
                "🚀 Готов? Ниже всё, что нужно:")
            keyboard = [
                [InlineKeyboardButton("🔗 Зарегистрироваться", callback_data="register"), InlineKeyboardButton("🆔 Отправить ID", callback_data="send_id")],
                [InlineKeyboardButton("📈 Получить сигнал", callback_data="get_signal")],
                [InlineKeyboardButton("🤝 Поддержка", url="https://t.me/razgondepoz1ta")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📚 <b>Справка по использованию бота</b>

🔹 <b>Основные команды:</b>
/start - Запуск бота
/help - Показать справку
/status - Статус подписки
/signals - Получить последние сигналы
/statistics - Статистика бота

🔹 <b>Типы подписок:</b>
• <b>Бесплатная</b> - 1 сигнал в день
• <b>Premium</b> - До 10 сигналов в день
• <b>VIP</b> - Неограниченные сигналы + приоритет

🔹 <b>Как использовать сигналы:</b>
1. Получите сигнал от бота
2. Откройте позицию на вашей платформе
3. Установите указанную сумму
4. Выберите время экспирации
5. Дождитесь результата

⚠️ <b>Важно:</b>
• Торговля бинарными опционами связана с рисками
• Не инвестируйте больше, чем можете позволить себе потерять
• Используйте сигналы как дополнительный инструмент анализа

📞 <b>Поддержка:</b>
По всем вопросам обращайтесь к администратору.
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start для регистрации.")
            return
        
        subscription_status = "✅ Активна" if self.db.is_user_subscribed(user_id) else "❌ Неактивна"
        subscription_type = user.get('subscription_type', 'free')
        expires_at = user.get('subscription_expires')
        
        status_text = f"""
📊 <b>Статус подписки</b>

👤 Пользователь: {user.get('first_name', 'Неизвестно')}
📅 Тип подписки: {subscription_type.upper()}
🔐 Статус: {subscription_status}
        """
        
        if expires_at:
            status_text += f"\n⏰ Истекает: {expires_at}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить подписку", callback_data="renew_subscription"), InlineKeyboardButton("📈 Получить сигналы", callback_data="get_signal")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            status_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signals command"""
        user_id = update.effective_user.id
        user = self.db.get_user(user_id)
        
        if not user or user.get('id_status') != 'confirmed':
            await update.message.reply_text(
                "⛔️ Доступ к сигналам пока закрыт.\n\nСначала зарегистрируйся 👉 https://bit.ly/4jb8a4k\nПотом скинь ID и пополни счёт — всё вручную проверяется.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
            )
            return
        
        await self.send_latest_signals(user_id, update.message.reply_text)
    
    async def statistics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /statistics command"""
        stats = self.signal_generator.get_statistics()
        
        stats_text = f"""
📈 <b>Статистика бота</b>

📊 Всего сигналов: {stats['total_signals']}
✅ Успешных: {stats['successful_signals']}
📈 Процент успеха: {stats['success_rate']:.1f}%
🕐 Последний сигнал: {stats['last_generated'].strftime('%H:%M:%S')}

🎯 <b>Текущие активные сигналы:</b>
        """
        
        active_signals = self.db.get_active_signals()
        if active_signals:
            for signal in active_signals[:5]:  # Show last 5 signals
                stats_text += f"""
🔸 {signal['asset']} - {signal['signal_type']}
   ⏱️ Экспирация: {signal['expiry_time']}
   📊 Точность: {signal['accuracy']}%
   🕐 Создан: {signal['created_at']}
                """
        else:
            stats_text += "\n📭 Нет активных сигналов"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks for registration flow and admin"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        is_admin = user_id == ADMIN_USER_ID
        data = query.data
        if is_admin:
            await self.handle_admin_callback(query, data)
            return
        await self.handle_user_callback(query, data)

    async def handle_admin_callback(self, query, data):
        if data == "admin_users":
            users = self.db.get_all_users()
            text = f"👥 Всего пользователей: {len(users)}\n" + "\n".join([str(uid) for uid in users])
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
        elif data == "admin_confirm":
            await query.edit_message_text("Введите команду /confirm ID для подтверждения пользователя.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]]))
        elif data == "admin_block":
            await query.edit_message_text("Введите команду /block ID для блокировки пользователя.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]]))
        elif data == "admin_signal":
            await query.edit_message_text("Введите команду /signal Актив Вход Время Срок для рассылки сигнала.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]]))
        elif data == "admin_send":
            await query.edit_message_text("Введите команду /send ID текст для личного сообщения.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]]))
        elif data == "admin_main_menu":
            await self.start_admin_menu(query)
        else:
            await query.edit_message_text("Выберите действие из меню.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]]))

    async def start_admin_menu(self, query):
        keyboard = [
            [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users"), InlineKeyboardButton("✅ Подтвердить ID", callback_data="admin_confirm")],
            [InlineKeyboardButton("🚫 Заблокировать", callback_data="admin_block"), InlineKeyboardButton("📢 Рассылка сигнала", callback_data="admin_signal")],
            [InlineKeyboardButton("✉️ Личное сообщение", callback_data="admin_send")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="admin_main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👋 <b>Привет, Админ!</b>\n\nТы в админ-меню. Здесь ты можешь:\n• Подтверждать/блокировать пользователей\n• Рассылать сигналы\n• Смотреть список юзеров\n• Писать от имени бота\n\nВыбери действие:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

    async def handle_user_callback(self, query, data):
        if data == "register":
            await query.edit_message_text(
                "Регистрируйся только по этой ссылке 👇\nhttps://bit.ly/4jb8a4k\n\n‼️ Без неё ты не попадёшь в базу, и бот не даст тебе сигналы.\nПосле регистрации — скинь ID сюда.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]])
            )
        elif data == "send_id":
            await query.edit_message_text(
                "📤 Напиши сюда свой ID после регистрации на платформе.\nЯ вручную проверю — и открою тебе доступ к сигналам.\n\nЕсли уже депнул — получишь доступ сразу.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]])
            )
        elif data == "get_signal":
            user = self.db.get_user(query.from_user.id)
            if not user or user.get('id_status') != 'confirmed':
                await query.edit_message_text(
                    "⛔️ Доступ к сигналам пока закрыт.\n\nСначала зарегистрируйся 👉 https://bit.ly/4jb8a4k\nПотом скинь ID и пополни счёт — всё вручную проверяется.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
                )
            else:
                signal = self.signal_generator.generate_signal('EUR/USD')
                if not signal:
                    await query.edit_message_text("😔 Сейчас нет сигнала. Попробуй позже.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]))
                else:
                    text = (
                        f"📢 Готово! Текущий сигнал:\n\n"
                        f"📍 Актив: {signal['asset']}\n"
                        f"📈 ВХОД: {'ВВЕРХ' if signal['signal_type']=='CALL' else 'ВНИЗ'}\n"
                        f"⏱ Время: сейчас\n"
                        f"⌛ Срок: 2 минуты\n"
                        f"💪 Уверенность: высокая\n\n"
                        f"👀 Заходи быстро — окно сделки может закрыться!"
                    )
                    keyboard = [
                        [InlineKeyboardButton("📊 Получить еще сигналы", callback_data="get_signal"), InlineKeyboardButton("📈 Статистика", callback_data="statistics")],
                        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
                    ]
                    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        elif data == "main_menu":
            await self.start_user_menu(query)
        elif data == "pay_premium":
            await self.handle_premium_subscription(query)
        elif data == "pay_vip":
            await self.handle_vip_subscription(query)
        elif data == "statistics":
            await self.handle_statistics(query)
        elif data == "get_signals":
            await self.handle_free_signals(query)
        elif data == "renew_subscription":
            await self.handle_renew_subscription(query)
        else:
            await query.edit_message_text("Выберите действие из меню.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]))

    async def start_user_menu(self, query):
        keyboard = [
            [InlineKeyboardButton("🔗 Зарегистрироваться", callback_data="register"), InlineKeyboardButton("🆔 Отправить ID", callback_data="send_id")],
            [InlineKeyboardButton("📈 Получить сигнал", callback_data="get_signal")],
            [InlineKeyboardButton("🤝 Поддержка", url="https://t.me/razgondepoz1ta")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👋 Привет, трейдер!\n\nТут работают только те, кто реально заходит в сделки и поднимает.\n\n📊 Я даю сигналы на вход. Что делать тебе — просто следовать.\n\nНо сначала — 3 шага:\n1. Регистрируешься по ссылке\n2. Скидываешь ID\n3. Депаешь — и получаешь доступ ко всем сигналам\n\n🚀 Готов? Ниже всё, что нужно:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_free_signals(self, query):
        """Handle free signals request"""
        user_id = query.from_user.id
        
        # Check if user already got free signal today
        user = self.db.get_user(user_id)
        if user and user.get('last_activity'):
            last_activity = datetime.fromisoformat(user['last_activity'].replace('Z', '+00:00'))
            if datetime.now() - last_activity < timedelta(days=1):
                await query.edit_message_text(
                    "⏰ Вы уже получили бесплатный сигнал сегодня. Попробуйте завтра или оформите подписку!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]),
                    parse_mode=ParseMode.HTML
                )
                return
        
        # Generate and send free signal
        signals = self.signal_generator.generate_signals_for_all_assets()
        if signals:
            signal = signals[0]  # Take first signal
            await self.send_signal_message(query.edit_message_text, signal, user_id)
        else:
            await query.edit_message_text(
                "😔 К сожалению, сейчас нет подходящих сигналов. Попробуйте позже!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]),
                parse_mode=ParseMode.HTML
            )
    
    async def handle_premium_subscription(self, query):
        """Handle premium subscription request"""
        subscription_text = f"""
💎 <b>Premium подписка</b>

📊 <b>Что включено:</b>
• До 10 сигналов в день
• Приоритетная доставка
• Расширенная аналитика
• Поддержка 24/7

💰 <b>Стоимость:</b> ${SUBSCRIPTION_PLANS['premium'] * 2} за {SUBSCRIPTION_PLANS['premium']} дней

💳 <b>Способы оплаты:</b>
• Банковская карта
• Криптовалюта
• Электронные кошельки

Для оформления подписки свяжитесь с администратором.
        """
        
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить", callback_data="pay_premium")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            subscription_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_vip_subscription(self, query):
        """Handle VIP subscription request"""
        subscription_text = f"""
👑 <b>VIP подписка</b>

📊 <b>Что включено:</b>
• Неограниченные сигналы
• Максимальный приоритет
• Персональный менеджер
• Эксклюзивные стратегии
• Анализ вашего портфеля

💰 <b>Стоимость:</b> ${SUBSCRIPTION_PLANS['vip'] * 3} за {SUBSCRIPTION_PLANS['vip']} дней

💳 <b>Способы оплаты:</b>
• Банковская карта
• Криптовалюта
• Электронные кошельки

Для оформления подписки свяжитесь с администратором.
        """
        
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить", callback_data="pay_vip")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            subscription_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_statistics(self, query):
        """Handle statistics request"""
        stats = self.signal_generator.get_statistics()
        
        stats_text = f"""
📈 <b>Статистика бота</b>

📊 Всего сигналов: {stats['total_signals']}
✅ Успешных: {stats['successful_signals']}
📈 Процент успеха: {stats['success_rate']:.1f}%
🕐 Последний сигнал: {stats['last_generated'].strftime('%H:%M:%S')}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_help(self, query):
        """Handle help request"""
        help_text = """
📚 <b>Справка по использованию бота</b>

🔹 <b>Основные команды:</b>
/start - Запуск бота
/help - Показать справку
/status - Статус подписки
/signals - Получить последние сигналы
/statistics - Статистика бота

🔹 <b>Типы подписок:</b>
• <b>Бесплатная</b> - 1 сигнал в день
• <b>Premium</b> - До 10 сигналов в день
• <b>VIP</b> - Неограниченные сигналы + приоритет

⚠️ <b>Важно:</b>
• Торговля бинарными опционами связана с рисками
• Не инвестируйте больше, чем можете позволить себе потерять
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_renew_subscription(self, query):
        """Handle subscription renewal request"""
        keyboard = [
            [InlineKeyboardButton("💎 Premium", callback_data="pay_premium"), InlineKeyboardButton("👑 VIP", callback_data="pay_vip")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💳 Выберите тип подписки для продления:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def send_signal_message(self, send_function, signal: dict, user_id: int):
        """Send formatted signal message"""
        signal_text = f"""
🚨 <b>НОВЫЙ СИГНАЛ</b>

📊 <b>Актив:</b> {signal['asset']}
🎯 <b>Тип:</b> {signal['signal_type']}
⏱️ <b>Экспирация:</b> {signal['expiry_time']}
💰 <b>Вход:</b> {signal['entry_price']}
🎯 <b>Цель:</b> {signal['target_price']}
🛑 <b>Стоп-лосс:</b> {signal['stop_loss']}
📈 <b>Точность:</b> {signal['accuracy']}%

⏰ <b>Время:</b> {signal['timestamp'].strftime('%H:%M:%S')}

💡 <b>Рекомендации:</b>
• Используйте 1-2% от депозита
• Следуйте указанным уровням
• Не торгуйте на эмоциях

⚠️ <b>Риск-менеджмент:</b>
Торговля бинарными опционами связана с высокими рисками.
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Получить еще сигналы", callback_data="get_signal"), InlineKeyboardButton("📈 Статистика", callback_data="statistics")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_function(
            signal_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        # Save signal to database
        signal_id = self.db.add_signal(
            asset=signal['asset'],
            signal_type=signal['signal_type'],
            expiry_time=signal['expiry_time'],
            entry_price=signal['entry_price'],
            target_price=signal['target_price'],
            stop_loss=signal['stop_loss'],
            accuracy=signal['accuracy']
        )
        
        logger.info(f"Signal sent to user {user_id}: {signal}")
    
    async def send_latest_signals(self, user_id: int, send_function):
        """Send latest signals to user"""
        # Check subscription
        if not self.db.is_user_subscribed(user_id):
            await send_function(
                "❌ У вас нет активной подписки. Оформите подписку для получения сигналов!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]),
                parse_mode=ParseMode.HTML
            )
            return
        
        # Get active signals
        active_signals = self.db.get_active_signals()
        
        if not active_signals:
            # Generate new signals
            signals = self.signal_generator.generate_signals_for_all_assets()
            if signals:
                for signal in signals[:3]:  # Send up to 3 signals
                    await self.send_signal_message(send_function, signal, user_id)
            else:
                await send_function(
                    "😔 К сожалению, сейчас нет подходящих сигналов. Попробуйте позже!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]),
                    parse_mode=ParseMode.HTML
                )
        else:
            # Send existing active signals
            for signal in active_signals[:3]:
                await self.send_signal_message(send_function, signal, user_id)
    
    async def broadcast_signals(self):
        """Broadcast signals to all subscribed users"""
        try:
            # Generate new signals
            signals = self.signal_generator.generate_signals_for_all_assets()
            
            if not signals:
                logger.info("No signals generated for broadcast")
                return
            
            # Get all subscribed users
            subscribed_users = self.db.get_subscribed_users()
            
            if not subscribed_users:
                logger.info("No subscribed users found")
                return
            
            # Send signals to all subscribed users
            for user_id in subscribed_users:
                try:
                    for signal in signals[:2]:  # Send up to 2 signals per broadcast
                        await self.send_signal_message(
                            lambda text, **kwargs: self.application.bot.send_message(user_id, text, **kwargs),
                            signal,
                            user_id
                        )
                        await asyncio.sleep(0.1)  # Small delay to avoid rate limiting
                except Exception as e:
                    logger.error(f"Error sending signal to user {user_id}: {e}")
                    continue
            
            logger.info(f"Broadcasted {len(signals)} signals to {len(subscribed_users)} users")
            
        except Exception as e:
            logger.error(f"Error in broadcast_signals: {e}")
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin commands (customized for new flow)"""
        user_id = update.effective_user.id
        if user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return
        if not context.args:
            await update.message.reply_text(
                "🔧 <b>Команды администратора:</b>\n\n"
                "/users — Список пользователей\n"
                "/send ID текст — Отправить личное сообщение\n"
                "/signal Актив Вход Время Срок — Рассылка сигнала вручную\n"
                "/confirm ID — Подтвердить доступ\n"
                "/block ID — Забанить юзера\n"
                "/check ID — Проверить статус",
                parse_mode=ParseMode.HTML
            )
            return
        command = context.args[0]
        if command == "users":
            users = self.db.get_all_users()
            text = f"👥 Всего пользователей: {len(users)}\n" + "\n".join([str(uid) for uid in users])
            await update.message.reply_text(text)
        elif command == "send" and len(context.args) >= 3:
            target_id = int(context.args[1])
            msg = " ".join(context.args[2:])
            try:
                await self.application.bot.send_message(target_id, f"✉️ Сообщение от админа:\n{msg}")
                await update.message.reply_text("✅ Сообщение отправлено.")
            except Exception:
                await update.message.reply_text("❌ Не удалось отправить сообщение.")
        elif command == "signal" and len(context.args) >= 5:
            asset, direction, time_str, expiry = context.args[1:5]
            text = (f"📢 Ручной сигнал!\n\n"
                    f"📍 Актив: {asset}\n"
                    f"📈 ВХОД: {direction}\n"
                    f"⏱ Время: {time_str}\n"
                    f"⌛ Срок: {expiry}\n"
                    f"💪 Уверенность: высокая")
            users = self.db.get_all_users()
            for uid in users:
                try:
                    await self.application.bot.send_message(uid, text)
                except Exception:
                    pass
            await update.message.reply_text("✅ Сигнал разослан.")
        elif command == "confirm" and len(context.args) == 2:
            target_id = int(context.args[1])
            self.db.confirm_user_id(target_id)
            await update.message.reply_text(f"✅ Доступ для {target_id} подтверждён.")
            try:
                await self.application.bot.send_message(target_id, "✅ Доступ к сигналам открыт! Можешь получать сигналы.")
            except Exception:
                pass
        elif command == "block" and len(context.args) == 2:
            target_id = int(context.args[1])
            self.db.block_user(target_id)
            await update.message.reply_text(f"🚫 Пользователь {target_id} заблокирован.")
            try:
                await self.application.bot.send_message(target_id, "🚫 Ваш доступ заблокирован администратором.")
            except Exception:
                pass
        elif command == "check" and len(context.args) == 2:
            target_id = int(context.args[1])
            user = self.db.get_user(target_id)
            if not user:
                await update.message.reply_text("❌ Пользователь не найден.")
            else:
                await update.message.reply_text(f"ID: {user.get('platform_id')}\nСтатус: {user.get('id_status')}")
        else:
            await update.message.reply_text("❌ Неизвестная команда или неверные параметры.")
    
    async def handle_id_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user sending platform ID"""
        user = update.effective_user
        user_id = user.id
        text = update.message.text.strip()
        # Проверяем, что это число (ID платформы)
        if not text.isdigit():
            await update.message.reply_text(
                "❗️ ID должен содержать только цифры. Попробуй ещё раз.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
            )
            return
        # Проверяем, не занят ли этот ID
        existing = self.db.get_user_by_platform_id(text)
        if existing and existing.get('user_id') != user_id:
            await update.message.reply_text(
                "⛔️ Этот ID уже используется другим пользователем.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
            )
            return
        # Сохраняем ID и сбрасываем статус на 'pending'
        self.db.set_platform_id(user_id, text)
        await update.message.reply_text(
            "✅ ID сохранён!\n\nОжидай подтверждения — после проверки ты получишь доступ к сигналам.\n\nЕсли уже депнул — доступ откроется сразу.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu"), InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
        # TODO: Запустить автонапоминания (через 30 мин, 1 час, 2 часа...)
    
    def setup_handlers(self):
        """Setup bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("signals", self.signals_command))
        self.application.add_handler(CommandHandler("statistics", self.statistics_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_id_message))
    
    def setup_scheduler(self):
        """Setup signal generation scheduler"""
        # Generate signals every 30 minutes
        schedule.every(30).minutes.do(self.run_signal_generation)
        
        # Broadcast signals every hour
        schedule.every().hour.do(self.run_broadcast)
    
    def run_signal_generation(self):
        """Run signal generation in background"""
        asyncio.create_task(self.broadcast_signals())
    
    def run_broadcast(self):
        """Run broadcast in background"""
        asyncio.create_task(self.broadcast_signals())
    
    async def run(self):
        """Run the bot"""
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not found in environment variables")
            return
        
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        self.setup_scheduler()
        
        logger.info("Starting Binary Options Signals Bot...")
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        try:
            # Keep the bot running
            while True:
                schedule.run_pending()
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

def run_http_stub():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), Handler)
    server.serve_forever()

threading.Thread(target=run_http_stub, daemon=True).start()

async def main():
    """Main function"""
    bot = BinaryOptionsBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main()) 