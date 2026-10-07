@echo off
setlocal
cd /d "%~dp0.."
if not exist work mkdir work
copy /y examples\vfs\deep.json work\stage4.json >nul
call run.bat --vfs work\stage4.json --script examples\scripts\stage4.txt
exit /b %errorlevel%
