@echo off
setlocal
cd /d "%~dp0.."
call run.bat --vfs examples\vfs\minimal.json --script examples\scripts\stage2.txt
if errorlevel 1 exit /b 1
call run.bat --script examples\scripts\stage2.txt
if errorlevel 1 exit /b 1
(echo exit) | call run.bat --vfs examples\vfs\minimal.json
if errorlevel 1 exit /b 1
(echo exit) | call run.bat
exit /b %errorlevel%
