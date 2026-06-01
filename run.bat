@echo off
cd /d "%~dp0"
echo === AiTest: מכין משתמשים ו-TOKEN ב-MongoDB ===
python create_users.py
if errorlevel 1 exit /b 1
echo.
echo === AiTest: מפעיל את האפליקציה ===
echo פתח בדפדפן: http://localhost:8501
echo לעצירה: Ctrl+C
echo.
streamlit run app.py
