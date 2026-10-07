@echo off
setlocal
cd /d "%~dp0.."
if not exist work mkdir work
copy /y examples\vfs\minimal.json work\minimal-b.json >nul
copy /y examples\vfs\files.json work\files-b.json >nul
copy /y examples\vfs\deep.json work\deep-b.json >nul
call run.bat --script examples\scripts\stage3.txt --vfs work\minimal-b.json
if errorlevel 1 exit /b 1
call run.bat --script examples\scripts\stage3.txt --vfs work\files-b.json
if errorlevel 1 exit /b 1
call run.bat --script examples\scripts\stage3.txt --vfs work\deep-b.json
exit /b %errorlevel%
