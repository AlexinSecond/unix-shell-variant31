@echo off
setlocal
cd /d "%~dp0.."
if not exist work mkdir work
copy /y examples\vfs\deep.json work\stage5.json >nul
call run.bat --vfs work\stage5.json --script examples\scripts\stage5.txt
exit /b %errorlevel%
