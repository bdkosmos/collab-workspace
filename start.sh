#!/bin/bash

echo "=========================================="
echo "  Collaborative Workspace - Запуск"
echo "=========================================="
echo

cd "$(dirname "$0")/backend"

echo "[1] Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "ОШИБКА: Python не установлен!"
    exit 1
fi

echo "[2] Проверка зависимостей..."
python3 -c "import fastapi" 2>/dev/null || {
    echo "Установка зависимостей..."
    pip3 install -r requirements.txt
}

echo
echo "[3] Запуск сервера..."
echo
echo "=========================================="
echo "  Сервер запущен на http://localhost:8000"
echo "  Откройте браузер по этому адресу"
echo "=========================================="
echo

python3 main.py
