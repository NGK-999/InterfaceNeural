@echo off
setlocal
set "PROJECT_DIR=%~dp0.."
if not exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    echo Ambiente virtual ausente. Siga a instalacao no README.md.
    exit /b 1
)
"%PROJECT_DIR%\.venv\Scripts\python.exe" -m muscle_monitor %*
exit /b %errorlevel%

