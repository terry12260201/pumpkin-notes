@echo off
chcp 65001 >nul
REM Pumpkin Notes 整理主機（PC-01 常駐）。當掉就自動重開；連續重開會發 Telegram 告訴南瓜。
REM 由工作排程器 PumpkinNotes_Worker 在登入時啟動；手動雙擊也行。
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set CRASHES=0
:loop
echo [%date% %time%] 啟動 worker.py >> worker.log
python worker.py >> worker.log 2>&1
set /a CRASHES+=1
echo [%date% %time%] worker.py 結束（第 %CRASHES% 次），30 秒後重開 >> worker.log
if %CRASHES% GEQ 3 (
  for /f "usebackq delims=" %%T in (`python -c "import json,os;d=json.load(open(os.path.expanduser('~/.config/pumpkin-notes/config.json'),encoding='utf-8'));print(d.get('telegram_bot_token',''))"`) do set TGT=%%T
  for /f "usebackq delims=" %%C in (`python -c "import json,os;d=json.load(open(os.path.expanduser('~/.config/pumpkin-notes/config.json'),encoding='utf-8'));print(d.get('telegram_chat_id',''))"`) do set TGC=%%C
  if not "%TGT%"=="" curl -s -o nul -X POST "https://api.telegram.org/bot%TGT%/sendMessage" --data-urlencode "chat_id=%TGC%" --data-urlencode "text=🎃 Pumpkin Notes 整理主機（PC-01）%0A🔴 worker 連續 %CRASHES% 次啟動失敗，請看 worker.log（%~dp0..\worker.log）" 
  set CRASHES=0
  timeout /t 300 /nobreak >nul
) else (
  timeout /t 30 /nobreak >nul
)
goto loop
