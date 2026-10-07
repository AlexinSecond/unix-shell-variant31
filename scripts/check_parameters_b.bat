@echo off
setlocal
cd /d "%~dp0.."
call run.bat --script "examples\scripts\stage2.txt" --vfs "examples\vfs\minimal.json"
if errorlevel 1 exit /b 1
call run.bat --script examples\scripts\stage2.txt
if errorlevel 1 exit /b 1
(echo exit) | call run.bat --vfs "examples\vfs\minimal.json"
if errorlevel 1 exit /b 1
call run.bat --help
if errorlevel 1 exit /b 1
call run.bat --bad-parameter
if not errorlevel 2 exit /b 1
call run.bat --script examples\scripts\missing.txt
if not errorlevel 1 exit /b 1
exit /b 0
