# Используем официальный Python-образ
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем только необходимые зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем только основной файл бота
COPY bot.py .

# Указываем порт для Cloud Run (не обязателен для Telegram-бота, но хорошая практика)
EXPOSE 8080

CMD ["python", "bot.py"] 