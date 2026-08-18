@echo off
echo ==========================================
echo   Collaborative Workspace - Запуск
echo ==========================================
echo.

cd /d "%~dp0\backend"

echo [1] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не установлен!
    echo Установите Python с https://python.org
    pause
    exit /b 1
)

echo [2] Проверка зависимостей...
python -c "import fastapi" 2>nul || (
    echo Установка зависимостей...
    pip install -r requirements.txt
)

echo.
echo [3] Запуск сервера...
echo.
echo ==========================================
echo   Сервер запущен на http://localhost:8000
echo   Откройте браузер по этому адресу
echo ==========================================
echo.

python main.py

pause
