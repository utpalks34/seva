@echo off
echo ============================================================
echo   SCFMS - Starting Daphne ASGI Server (WebSocket enabled)
echo ============================================================
pushd "%~dp0"
set DJANGO_SETTINGS_MODULE=scfms_backend.settings
echo.
echo Starting on http://127.0.0.1:8000
echo WebSocket: ws://127.0.0.1:8000/ws/notifications/
echo.
venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 scfms_backend.asgi:application
popd
pause
