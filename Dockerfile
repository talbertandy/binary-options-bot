# Используем официальный Python-образ
FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Указываем порт для Cloud Run (не обязателен для Telegram-бота, но хорошая практика)
EXPOSE 8080

CMD ["python", "bot.py"] 