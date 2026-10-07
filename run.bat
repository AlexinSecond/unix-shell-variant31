@echo off
setlocal
cd /d "%~dp0"
if defined PYTHON_EXE (
  "%PYTHON_EXE%" -m src %*
) else (
  python -m src %*
)
exit /b %errorlevel%
