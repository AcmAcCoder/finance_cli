@echo off
rem ============================================================
rem  Double-click this file to start the app.
rem
rem  KEEP THIS FILE PURE ASCII. Do not add Chinese (or any
rem  non-ASCII) characters or comments here.
rem  cmd.exe reads .bat files using the system ANSI codepage
rem  (CP936/GBK on Chinese Windows), but this file is saved as
rem  UTF-8. Non-ASCII bytes get mis-decoded, and the mangled
rem  bytes can even swallow the line break, gluing two lines
rem  together and breaking the whole script.
rem  Chinese instructions live in README.md instead.
rem ============================================================
rem %~dp0 is the folder containing this .bat file.
rem /d switches the drive too, so double-clicking works from
rem any location, not just from this drive.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [ERROR] Virtual environment not found: .venv\Scripts\python.exe
    echo.
    echo Run the "first time setup" steps in README.md, then try again.
    echo.
    pause
    exit /b 1
)

.venv\Scripts\python.exe -m streamlit run app.py

rem If the command above fails and exits, the window would close
rem instantly and you would never see the error. So hold it open.
pause
