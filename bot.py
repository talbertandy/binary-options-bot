import logging
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

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
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id
        
        # Add user to database
        self.db.add_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        welcome_message = f"""
🚀 Добро пожаловать в Binary Options Signals Bot!

👋 Привет, {user.first_name}!

📊 Я предоставляю точные торговые сигналы для бинарных опционов с использованием продвинутого технического анализа.

🎯 Мои возможности:
• Точные сигналы CALL/PUT
• Множественные торговые пары
• Различные временные фреймы
• Высокая точность сигналов
• Автоматическая рассылка

💡 Для начала работы выберите подписку:
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Бесплатные сигналы", callback_data="free_signals")],
            [InlineKeyboardButton("💎 Premium подписка", callback_data="premium")],
            [InlineKeyboardButton("👑 VIP подписка", callback_data="vip")],
            [InlineKeyboardButton("📈 Статистика", callback_data="statistics")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
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
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
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
            [InlineKeyboardButton("🔄 Обновить подписку", callback_data="renew_subscription")],
            [InlineKeyboardButton("📈 Получить сигналы", callback_data="get_signals")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            status_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signals command"""
        await self.send_latest_signals(update.effective_user.id, update.message.reply_text)
    
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
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "free_signals":
            await self.handle_free_signals(query)
        elif query.data == "premium":
            await self.handle_premium_subscription(query)
        elif query.data == "vip":
            await self.handle_vip_subscription(query)
        elif query.data == "statistics":
            await self.handle_statistics(query)
        elif query.data == "help":
            await self.handle_help(query)
        elif query.data == "get_signals":
            await self.send_latest_signals(user_id, query.edit_message_text)
        elif query.data == "renew_subscription":
            await self.handle_renew_subscription(query)
    
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
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
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
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
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
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
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
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
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
            [InlineKeyboardButton("💎 Premium", callback_data="pay_premium")],
            [InlineKeyboardButton("👑 VIP", callback_data="pay_vip")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
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
            [InlineKeyboardButton("📊 Получить еще сигналы", callback_data="get_signals")],
            [InlineKeyboardButton("📈 Статистика", callback_data="statistics")]
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
        """Handle admin commands"""
        user_id = update.effective_user.id
        
        if user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "🔧 <b>Команды администратора:</b>\n\n"
                "/admin broadcast - Отправить сигналы всем пользователям\n"
                "/admin stats - Показать статистику\n"
                "/admin users - Список пользователей\n"
                "/admin signal - Создать сигнал вручную",
                parse_mode=ParseMode.HTML
            )
            return
        
        command = context.args[0]
        
        if command == "broadcast":
            await self.broadcast_signals()
            await update.message.reply_text("✅ Сигналы отправлены всем подписчикам!")
        
        elif command == "stats":
            stats = self.signal_generator.get_statistics()
            users = self.db.get_all_users()
            subscribed_users = self.db.get_subscribed_users()
            
            stats_text = f"""
📊 <b>Статистика бота</b>

👥 Всего пользователей: {len(users)}
✅ Подписчиков: {len(subscribed_users)}
📈 Сигналов сгенерировано: {stats['total_signals']}
🎯 Процент успеха: {stats['success_rate']:.1f}%
            """
            
            await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
        
        elif command == "users":
            users = self.db.get_all_users()
            users_text = f"👥 Всего пользователей: {len(users)}\n\n"
            
            for i, user_id in enumerate(users[:10], 1):  # Show first 10 users
                user = self.db.get_user(user_id)
                if user:
                    users_text += f"{i}. {user.get('first_name', 'Unknown')} (@{user.get('username', 'no_username')})\n"
            
            if len(users) > 10:
                users_text += f"\n... и еще {len(users) - 10} пользователей"
            
            await update.message.reply_text(users_text)
        
        elif command == "signal":
            if len(context.args) < 4:
                await update.message.reply_text(
                    "❌ Использование: /admin signal <asset> <type> <expiry> [accuracy]"
                )
                return
            
            asset = context.args[1]
            signal_type = context.args[2]
            expiry_time = context.args[3]
            accuracy = float(context.args[4]) if len(context.args) > 4 else 85.0
            
            signal = {
                'asset': asset,
                'signal_type': signal_type,
                'expiry_time': expiry_time,
                'entry_price': 1.0000,
                'target_price': 1.0010,
                'stop_loss': 0.9990,
                'accuracy': accuracy,
                'timestamp': datetime.now()
            }
            
            await self.broadcast_signals()
            await update.message.reply_text(f"✅ Сигнал создан и отправлен: {asset} {signal_type}")
    
    def setup_handlers(self):
        """Setup bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("signals", self.signals_command))
        self.application.add_handler(CommandHandler("statistics", self.statistics_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
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

async def main():
    """Main function"""
    bot = BinaryOptionsBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main()) 