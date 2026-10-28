@echo off
setlocal
cd /d "%~dp0"
title Trading AI Analyzer

echo ======================================
echo       TRADING AI ANALYZER
echo ======================================
echo.

where python >nul 2>nul
if errorlevel 1 goto no_python

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Python virtual muhit yaratilmoqda...
    python -m venv .venv
    if errorlevel 1 goto setup_error
)

echo [2/3] Kerakli kutubxonalar tekshirilmoqda va o'rnatilmoqda...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto setup_error

echo.
echo OpenAI API kaliti kerak. Uni o'zingiz OpenAI platformasidan oling.
echo Kalit maxfiy: hech kimga yubormang va chatga joylamang.
echo.
if not defined OPENAI_API_KEY set /p OPENAI_API_KEY=OpenAI API kalitini kiriting: 
if not defined OPENAI_API_KEY goto no_key

echo [3/3] Backend ishga tushmoqda...
start "Trading AI Backend" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak >nul
start "" "%~dp0index.html"
echo.
echo Sahifa brauzerda ochildi.
echo AI tahlil ishlashi uchun backend oynasini yopmang.
echo Ushbu oynani yopishingiz mumkin.
pause
goto end

:no_python
echo Python topilmadi. Python 3.12 o'rnating va run.bat ni qayta oching.
pause
goto end

:setup_error
echo Kutubxonalar o'rnatilmadi. Internet va Python versiyasini tekshiring.
pause
goto end

:no_key
echo API kaliti kiritilmadi. run.bat ni qayta ishga tushiring.
pause

:end
endlocal
