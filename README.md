# 🤖 Binary Options Signals Bot

Telegram-бот для рассылки точных торговых сигналов по бинарным опционам с возможностью автоматизации и платного доступа.

## 🚀 Возможности

- 📊 **Точные сигналы** - Генерация сигналов на основе технического анализа
- 💎 **Платные подписки** - Система подписок (Basic, Premium, VIP)
- 🔄 **Автоматическая рассылка** - Отправка сигналов по расписанию
- 📈 **Статистика** - Отслеживание успешности сигналов
- 👥 **Управление пользователями** - База данных пользователей и подписок
- 🔧 **Админ-панель** - Управление ботом через команды

## 🛠 Технологии

- **Backend**: Python 3.8+
- **Telegram API**: python-telegram-bot
- **База данных**: SQLite
- **Технический анализ**: pandas, numpy, ccxt
- **Планировщик**: schedule

## 📋 Требования

- Python 3.8 или выше
- Telegram Bot Token
- Доступ к интернету

## 🚀 Установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/your-username/binary-options-bot.git
cd binary-options-bot
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Создайте файл .env:**
```bash
BOT_TOKEN=ваш_токен_бота
ADMIN_USER_ID=ваш_telegram_id
```

4. **Запустите бота:**
```bash
python bot.py
```

## 📱 Использование

### Основные команды:
- `/start` - Запуск бота
- `/help` - Справка
- `/status` - Статус подписки
- `/signals` - Получить сигналы
- `/statistics` - Статистика

### Админ команды:
- `/admin broadcast` - Отправить сигналы всем
- `/admin stats` - Статистика бота
- `/admin users` - Список пользователей
- `/admin signal` - Создать сигнал вручную

## 💰 Система подписок

### Бесплатная
- 1 сигнал в день
- Базовые функции

### Premium ($60/90 дней)
- До 10 сигналов в день
- Приоритетная доставка
- Расширенная аналитика

### VIP ($540/180 дней)
- Неограниченные сигналы
- Максимальный приоритет
- Персональный менеджер
- Эксклюзивные стратегии

## 🔧 Конфигурация

Основные настройки в файле `config.py`:

```python
# Торговые пары
ASSETS = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD']

# Временные фреймы
EXPIRY_TIMES = ['1m', '5m', '15m', '30m', '1h']

# Планы подписок
SUBSCRIPTION_PLANS = {
    'basic': 30,
    'premium': 90,
    'vip': 180
}
```

## 📊 Технический анализ

Бот использует следующие индикаторы:
- **RSI** (Relative Strength Index)
- **MACD** (Moving Average Convergence Divergence)
- **Bollinger Bands**
- **Stochastic Oscillator**

## 🔮 Планы развития

### Версия 2.0
- [ ] Интеграция с TradingView Webhook
- [ ] Веб-интерфейс с графиками
- [ ] Автоторговля по API
- [ ] Push-уведомления
- [ ] ML-алгоритмы для анализа

### Версия 3.0
- [ ] Поддержка криптовалют
- [ ] Мобильное приложение
- [ ] Социальные функции
- [ ] Копирование сделок

## 📝 Лицензия

MIT License

## ⚠️ Отказ от ответственности

Торговля бинарными опционами связана с высокими рисками. Используйте сигналы на свой страх и риск. Не инвестируйте больше, чем можете позволить себе потерять.

## 🤝 Поддержка

По всем вопросам обращайтесь к разработчику или создавайте Issues в репозитории.

---

**Создано с ❤️ для трейдеров** 