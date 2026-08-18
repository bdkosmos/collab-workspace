@echo off
echo ==========================================
echo   Collaborative Workspace - Установка
echo ==========================================
echo.

cd /d "%~dp0"

echo [1] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не установлен!
    pause
    exit /b 1
)

echo [2] Установка зависимостей...
cd backend
pip install -r requirements.txt

echo.
echo ==========================================
echo   Установка завершена!
echo.
echo   Для запуска выполните:
echo   start.bat
echo.
echo   Или вручную:
echo   cd backend
echo   python main.py
echo ==========================================
pause
