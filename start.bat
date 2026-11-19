@echo off
cd /d "%~dp0"
docker compose up -d
cd frontend
start "" http://localhost:5173
call npm run dev
