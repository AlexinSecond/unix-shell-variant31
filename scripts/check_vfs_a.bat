@echo off
setlocal
cd /d "%~dp0.."
if not exist work mkdir work
copy /y examples\vfs\minimal.json work\minimal.json >nul
copy /y examples\vfs\files.json work\files.json >nul
copy /y examples\vfs\deep.json work\deep.json >nul
call run.bat --vfs work\minimal.json --script examples\scripts\stage3.txt
if errorlevel 1 exit /b 1
call run.bat --vfs work\files.json --script examples\scripts\stage3.txt
if errorlevel 1 exit /b 1
call run.bat --vfs work\deep.json --script examples\scripts\stage3.txt
exit /b %errorlevel%
