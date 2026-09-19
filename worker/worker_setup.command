#!/bin/bash
# 第一次設定整理主機：貼兩把金鑰（只存在這台電腦的 ~/.config/pumpkin-notes/config.json，不進 repo）
CONF="$HOME/.config/pumpkin-notes/config.json"
echo "── Pumpkin Notes 整理主機設定 ──"
echo "1) Supabase secret key：後台 → Project Settings → API Keys → Secret keys → default → 眼睛圖示 → 複製（sb_secret_ 開頭）"
read -r -p "貼上 Supabase secret key：" SBK
echo "2) Claude API key：https://console.anthropic.com → API Keys → Create Key（sk-ant- 開頭）"
read -r -p "貼上 Claude API key：" AK
python3 - "$SBK" "$AK" <<'PY'
import json, sys, os
from pathlib import Path
p = Path.home() / ".config/pumpkin-notes/config.json"
p.parent.mkdir(parents=True, exist_ok=True)
d = json.loads(p.read_text()) if p.exists() else {}
d["supabase_url"] = "https://xoyalmkdaiehsldbokud.supabase.co"
if sys.argv[1].strip(): d["supabase_service_key"] = sys.argv[1].strip()
if sys.argv[2].strip(): d["anthropic_api_key"] = sys.argv[2].strip()
d.setdefault("model", "claude-opus-5")
p.write_text(json.dumps(d, ensure_ascii=False, indent=2)); os.chmod(p, 0o600)
print("✅ 已存到", p)
PY
python3 -c "import anthropic" 2>/dev/null || pip3 install -q anthropic
echo "完成。接著雙擊「啟動整理主機.command」。"
read -r -p "按 Enter 關閉…"
