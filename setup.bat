@echo off
cd /d "%~dp0"
where docker >nul 2>nul || (echo Install Docker Desktop first: https://www.docker.com/products/docker-desktop & pause & exit /b 1)
where npm >nul 2>nul || (echo Install Node.js 20+ first: https://nodejs.org & pause & exit /b 1)
if not exist .env (
  copy .env.example .env >nul
  powershell -NoProfile -Command "$s=[Convert]::ToBase64String((1..48|%%{[byte](Get-Random -Maximum 256)})); (Get-Content .env) -replace '^JWT_SECRET=.*',('JWT_SECRET='+$s) | Set-Content -Encoding ascii .env"
  echo Created .env with a random JWT_SECRET.
)
docker compose up -d --build || (echo Docker failed. Is Docker Desktop running? & pause & exit /b 1)
cd frontend
call npm install
echo.
echo Setup finished. Run start.bat to open the site.
pause
