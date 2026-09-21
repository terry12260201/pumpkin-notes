#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PC-01 第一次設定：把 Mac 帶來的 config.json 補上這台專用的欄位（機器名、Telegram、路徑）。
用法：python 加設定.py
會問：worker_name、telegram_bot_token、telegram_chat_id；並把 Mac 專用路徑（vault_dir/share_dir/work_dir/skill_dir）改成這台的。
"""
import json, os, sys
from pathlib import Path
p = Path(os.path.expanduser(os.environ.get("PN_CONFIG") or "~/.config/pumpkin-notes/config.json"))
if not p.exists(): sys.exit(f"找不到 {p}：先把 Mac 的 config.json 放到這裡（見 PC01_接手.md）")
d = json.loads(p.read_text(encoding="utf-8"))
def ask(k, tip, default=""):
    cur = d.get(k) or default
    v = input(f"{k}（{tip}）[{cur}]：").strip()
    d[k] = v or cur
ask("worker_name", "顯示在網站與通知的機器名", "PC-01")
ask("telegram_bot_token", "沿用公告欄／允和 bot 的 token，只用來發訊息")
ask("telegram_chat_id", "要收壞消息的 chat id（南瓜私聊或管理群）")
ask("skill_dir", "pumpkin-digital-notes 的 scripts 資料夾", str(Path.home() / ".claude/skills/pumpkin-digital-notes/scripts"))
base = Path.home() / "PumpkinNotes"
for k in ("vault_dir", "share_dir", "work_dir"):
    d[k] = str(base / {"vault_dir": "notes", "share_dir": "site", "work_dir": "work"}[k])   # 這台沒有 Obsidian vault，全部放本機暫存
d["base_url"] = ""; d.setdefault("poll_fallback_sec", 120)
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print("✅ 已寫入", p, "\n接著雙擊 啟動整理主機.bat")
